import razorpay
import os
from django.db.models import F 
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Booking
from routes.models import Route
from accounts.models import BusDetails
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
            is_verified=False 
        )

        return Response({
            "ticket_id": booking.ticket_id,
            "bus_name": booking.bus.bus_name,
            "from": booking.from_loc,
            "to": booking.to_loc,
            "date": booking.created_at.strftime("%Y-%m-%d %H:%M")
        }, status=status.HTTP_201_CREATED)

    except razorpay.errors.SignatureVerificationError:
        return Response({"error": "Payment Verification Failed"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

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
                "date": booking.created_at.strftime("%Y-%m-%d %H:%M"),
                "is_verified": booking.is_verified
            })
            
        return Response(ticket_data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)