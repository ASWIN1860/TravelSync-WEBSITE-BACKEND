import razorpay
import os
from django.db.models import F 
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Booking
from routes.models import Route
from accounts.models import BusDetails, Wallet, WalletTransaction
import random
import string
from decimal import Decimal
from decouple import config
import razorpay


RAZORPAY_KEY_ID = config('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = config('RAZORPAY_KEY_SECRET')

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

def generate_ticket_id():
    return "TKT-" + ''.join(random.choices(string.digits, k=6))

# ==========================================
#  2. PAYMENT FLOW
# ==========================================

@api_view(['POST'])
@permission_classes([AllowAny])
def initiate_payment(request):
    amount = request.data.get('amount') 
    if not amount: return Response({"error": "Amount is required"}, 400)
    
    try:
        data = { "amount": int(amount) * 100, "currency": "INR", "payment_capture": "1" }
        order = client.order.create(data=data)
        return Response({
            "order_id": order['id'], 
            "amount": data['amount'], 
            "key": RAZORPAY_KEY_ID
        })
    except Exception as e:
        return Response({"error": str(e)}, 400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    """ Step 2: Verify & Create Ticket """
    data = request.data
    
    # Extract Data
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_signature = data.get('razorpay_signature')
    
    route_id = data.get('route_id')
    from_loc = data.get('from')
    to_loc = data.get('to')
    price = data.get('price')
    passenger_count = data.get('passenger_count', 1)

    params_dict = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature
    }

    try:
        # 1. Verify Signature
        client.utility.verify_payment_signature(params_dict)
        
        # 2. Get Bus & Create Ticket
        route = Route.objects.get(id=route_id)
        
        ticket_id = generate_ticket_id()
        while Booking.objects.filter(ticket_id=ticket_id).exists():
            ticket_id = generate_ticket_id()

        booking = Booking.objects.create(
            ticket_id=ticket_id,
            user=request.user, # NEW: Associate ticket with logged in user
            bus=route.bus,
            route=route,
            from_loc=from_loc,
            to_loc=to_loc,
            price=price,
            passenger_count=passenger_count,
            is_verified=False 
        )

        return Response({
            "ticket_id": booking.ticket_id,
            "bus_name": booking.bus.bus_name,
            "from": booking.from_loc,
            "to": booking.to_loc,
            "passenger_count": booking.passenger_count,
            "date": booking.created_at.strftime("%Y-%m-%d %H:%M")
        }, status=status.HTTP_201_CREATED)

    except razorpay.errors.SignatureVerificationError:
        return Response({"error": "Payment Verification Failed"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pay_with_wallet(request):
    """ Step 2: Pay entirely with TravelCoins & Create Ticket """
    data = request.data
    
    route_id = data.get('route_id')
    from_loc = data.get('from')
    to_loc = data.get('to')
    price = data.get('price')
    passenger_count = data.get('passenger_count', 1)

    try:
        wallet = Wallet.objects.get(user=request.user)
        total_cost = Decimal(str(price)) * int(passenger_count)
        
        if wallet.balance < total_cost:
            return Response({"error": "Insufficient TravelCoins"}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Get Route (Do this first to ensure it's valid before charging)
        route = Route.objects.get(id=route_id)

        # 2. Deduct from User Wallet
        wallet.balance -= total_cost
        wallet.save()

        # Log User Transaction
        WalletTransaction.objects.create(
            wallet=wallet,
            amount=-total_cost,
            description=f"Purchased {passenger_count} ticket(s) from {from_loc} to {to_loc}"
        )
        
        # 3. Create Ticket
        ticket_id = generate_ticket_id()
        while Booking.objects.filter(ticket_id=ticket_id).exists():
            ticket_id = generate_ticket_id()

        booking = Booking.objects.create(
            ticket_id=ticket_id,
            user=request.user,
            bus=route.bus,
            route=route,
            from_loc=from_loc,
            to_loc=to_loc,
            price=price,
            passenger_count=passenger_count,
            is_verified=False 
        )

        return Response({
            "ticket_id": booking.ticket_id,
            "bus_name": booking.bus.bus_name,
            "from": booking.from_loc,
            "to": booking.to_loc,
            "passenger_count": booking.passenger_count,
            "date": booking.created_at.strftime("%Y-%m-%d %H:%M")
        }, status=status.HTTP_201_CREATED)

    except Wallet.DoesNotExist:
        return Response({"error": "Wallet not found"}, status=status.HTTP_404_NOT_FOUND)
    except Route.DoesNotExist:
        return Response({"error": "Route not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ==========================================
#  3. OPERATOR VERIFICATION
# ==========================================

@api_view(['POST'])
@permission_classes([IsAuthenticated]) 
def verify_ticket(request):
    ticket_id = request.data.get('ticket_id')
    try:
        operator_bus = BusDetails.objects.get(user=request.user)
        ticket = Booking.objects.get(ticket_id=ticket_id)

        if ticket.bus.id != operator_bus.id:
            return Response({"error": "Invalid Bus! Ticket belongs to another operator."}, 403)

        if ticket.is_verified:
            return Response({"error": "Ticket already used."}, 400)

        ticket.is_verified = True
        ticket.save()

        # --- FINANCIAL SAFETY FIX ---
        operator_bus.total_earnings = F('total_earnings') + Decimal(str(ticket.price))
        operator_bus.save()
        
        operator_bus.refresh_from_db() 

        return Response({
            "message": "Verified!", 
            "transfer_msg": f"₹{ticket.price} added to wallet."
        }, 200)

    except (BusDetails.DoesNotExist, Booking.DoesNotExist):
        return Response({"error": "Invalid Request"}, 404)

# ==========================================
#  4. USER TICKETS
# ==========================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_tickets(request):
    try:
        # Fetch tickets for the logged in user, newest first
        bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
        
        ticket_data = []
        for booking in bookings:
            ticket_data.append({
                "ticket_id": booking.ticket_id,
                "bus_name": booking.bus.bus_name,
                "from_loc": booking.from_loc,
                "to_loc": booking.to_loc,
                "price": str(booking.price),
                "passenger_count": booking.passenger_count,
                "date": booking.created_at.strftime("%Y-%m-%d %H:%M"),
                "is_verified": booking.is_verified
            })
            
        return Response(ticket_data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ==========================================
#  5. WITHDRAW FUNDS (BUS OPERATOR)
# ==========================================

from accounts.models import BusDetails, WithdrawalRequest

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def withdraw_funds(request):
    try:
        operator_bus = BusDetails.objects.get(user=request.user)
        amount = Decimal(str(request.data.get('amount', 0)))
        
        if amount <= 0:
            return Response({"error": "Invalid amount"}, status=400)
            
        if operator_bus.total_earnings < amount:
            return Response({"error": "Insufficient TC earnings to withdraw."}, status=400)
            
        # Deduct from earnings securely
        operator_bus.total_earnings -= amount
        operator_bus.save()
        
        # Create persistent request
        WithdrawalRequest.objects.create(
            user=request.user,
            amount=amount,
            account_name=request.data.get('account_name'),
            bank_name=request.data.get('bank_name'),
            account_number=request.data.get('account_number'),
            ifsc_code=request.data.get('ifsc_code')
        )
        return Response({"message": "Withdrawal requested successfully"}, status=201)
        
    except BusDetails.DoesNotExist:
        return Response({"error": "Only Bus Operators can withdraw earnings."}, status=403)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_withdraw_history(request):
    try:
        # Check if they are a bus operator
        BusDetails.objects.get(user=request.user)
        
        history = WithdrawalRequest.objects.filter(user=request.user).order_by('-created_at')
        
        data = []
        for req in history:
            data.append({
                "id": req.id,
                "amount": str(req.amount),
                "bank_name": req.bank_name,
                "account_number": req.account_number[-4:] if len(req.account_number) >= 4 else req.account_number, # Only show last 4 digits
                "status": req.status,
                "date": req.created_at.strftime("%Y-%m-%d %H:%M")
            })
            
        return Response(data, status=200)
    except BusDetails.DoesNotExist:
        return Response({"error": "Only Bus Operators can view withdrawal history."}, status=403)
    except Exception as e:
        return Response({"error": str(e)}, status=500)