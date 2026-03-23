from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from .serializers import RegisterSerializer, UserSerializer, BusRegisterSerializer, SetNewPasswordSerializer
from .models import BusDetails, Wallet, WalletTransaction
import logging
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .tokens import custom_token_generator # <--- CRITICAL IMPORT
import random


logger = logging.getLogger(__name__)


OTP_STORE = {}

@api_view(['POST'])
@permission_classes([AllowAny])
def send_email_otp(request):
    email = request.data.get('email')

    if not email:
        return Response({"error": "Email required"}, status=400)

    # generate 6 digit otp
    otp = str(random.randint(100000, 999999))

    # store otp
    OTP_STORE[email] = otp

    subject = "TravelZync Email Verification OTP"
    message = f"Your TravelZync OTP is: {otp}\n\nThis OTP will be used to verify your email."

    try:
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )

        return Response({"message": "OTP sent to email"})
    except Exception as e:
        print("EMAIL ERROR:", e)
        return Response({"error": f"Failed to send OTP: {str(e)}"}, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_email_otp(request):
    email = request.data.get("email")
    otp = request.data.get("otp")

    stored_otp = OTP_STORE.get(email)

    if stored_otp and stored_otp == otp:
        return Response({"verified": True})

    return Response({"verified": False, "error": "Invalid OTP"}, status=400)

# ==========================================
# 1. AUTHENTICATION (Register/Login)
# ==========================================

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            "user": UserSerializer(user).data,
            "token": token.key,
            "role": "user",
            "message": "Account created successfully"
        })

@api_view(['POST'])
def register_bus_view(request):
    serializer = BusRegisterSerializer(data=request.data)
    if serializer.is_valid():
        bus_details = serializer.save(status='pending')
        user = bus_details.user
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            "user": UserSerializer(user).data,
            "token": token.key,
            "role": "bus",
            "message": "Bus Registered successfully"
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def check_availability(request):
    username = request.query_params.get('username')
    email = request.query_params.get('email')
    
    if username:
        is_taken = User.objects.filter(username__iexact=username).exists()
        return Response({'available': not is_taken, 'field': 'username'})
    
    if email:
        is_taken = User.objects.filter(email__iexact=email).exists()
        return Response({'available': not is_taken, 'field': 'email'})

    reg_number = request.query_params.get('reg_number')
    if reg_number:
        is_taken = BusDetails.objects.filter(reg_number__iexact=reg_number).exists()
        return Response({'available': not is_taken, 'field': 'reg_number'})


    phone = request.query_params.get('phone')
    if phone:
        is_taken = BusDetails.objects.filter(phone_number=phone).exists()
        return Response({'available': not is_taken, 'field': 'phone'})
        
    return Response({'error': 'Missing query param'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def login_view(request):
    try:
        email = request.data.get('email')
        password = request.data.get('password')

        logger.info(f"Login Attempt: {email}") 

        if not email or not password:
            return Response({'error': 'Please provide both email and password'}, status=status.HTTP_400_BAD_REQUEST)

        user_obj = User.objects.filter(email__iexact=email).first()

        if user_obj is None:
            logger.warning(f"Login Failed: Email not found - {email}")
            return Response({'error': 'User with this email does not exist'}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(username=user_obj.username, password=password)

        if user is not None:
            token, created = Token.objects.get_or_create(user=user)
            
            # Determine Role
            if user.is_superuser:
                role = "admin"
            else:
                is_bus_operator = hasattr(user, 'bus_details') 
                if is_bus_operator:
                    if user.bus_details.status == 'pending':
                        logger.warning(f"Login Failed: Bus Account Pending - {email}")
                        return Response({"error": "Your bus operator account is pending admin approval."}, status=status.HTTP_403_FORBIDDEN)
                    if user.bus_details.status == 'rejected':
                        logger.warning(f"Login Failed: Bus Account Rejected - {email}")
                        return Response({"error": "Your bus operator account registration was rejected."}, status=status.HTTP_403_FORBIDDEN)
                    role = "bus"
                else:
                    role = "user"

            logger.info(f"Login Success: {user.username} ({role})")
            return Response({
                "token": token.key,
                "user": UserSerializer(user).data,
                "role": role,
                "message": "Login successful"
            })
        
        logger.warning(f"Login Failed: Invalid Password - {email}")
        return Response({"error": "Invalid Password"}, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(f"Login Server Error: {str(e)}")
        return Response({"error": "Server Error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ==========================================
# 2. PROFILE MANAGEMENT
# ==========================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_upi(request):
    upi_id = request.data.get('upi_id')
    if not upi_id or '@' not in upi_id:
        return Response({"error": "Invalid UPI ID format"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        bus_details = BusDetails.objects.get(user=request.user)
        bus_details.upi_id = upi_id
        bus_details.save()
        return Response({"message": "UPI ID Linked Successfully!", "upi_id": upi_id})
    except BusDetails.DoesNotExist:
        return Response({"error": "Bus Operator profile not found"}, status=status.HTTP_404_NOT_FOUND)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_booking_status(request):
    try:
        bus = BusDetails.objects.get(user=request.user)
        bus.is_booking_open = not bus.is_booking_open
        bus.save()
        return Response({
            "status": bus.is_booking_open, 
            "message": f"Online Booking is now {'ON' if bus.is_booking_open else 'OFF'}"
        })
    except BusDetails.DoesNotExist:
        return Response({"error": "Bus profile not found"}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_crowd_status(request):
    status_choice = request.data.get('status')
    if status_choice not in ['green', 'yellow', 'red']:
        return Response({"error": "Invalid status choice"}, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        bus = BusDetails.objects.get(user=request.user)
        bus.crowd_status = status_choice
        bus.save()
        return Response({
            "crowd_status": bus.crowd_status,
            "message": f"Crowd status updated to {status_choice.title()}"
        })
    except BusDetails.DoesNotExist:
        return Response({"error": "Bus profile not found"}, status=404)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_bus_profile(request):
    try:
        bus = BusDetails.objects.get(user=request.user)
        return Response({
            "upi_id": bus.upi_id,
            "total_earnings": bus.total_earnings,
            "is_booking_open": bus.is_booking_open, 
            "crowd_status": bus.crowd_status,
        })
    except BusDetails.DoesNotExist:
        return Response({"error": "Bus profile not found"}, status=404)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    return Response({
        "username": request.user.username,
        "email": request.user.email,
        "is_bus_operator": hasattr(request.user, 'bus_details')
    })

# ==========================================
# 3. FORGOT PASSWORD (Single, Correct Version)
# ==========================================

@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password_request(request):
    email = request.data.get('email')

    if not User.objects.filter(email=email).exists():
        return Response({'message': 'If an account exists, a reset link has been sent.'}, status=status.HTTP_200_OK)

    user = User.objects.get(email=email)
    
    # 1. Generate Token
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = custom_token_generator.make_token(user) 
    
    # =====================================================
    # 2. IMMEDIATE DEBUG CHECK (The Sanity Check)
    # =====================================================
    print("\n" + "="*50)
    print("DEBUG: TESTING TOKEN IMMEDIATELY IN VIEW...")
    is_valid_now = custom_token_generator.check_token(user, token)
    print(f"DEBUG: Token generated: {token}")
    print(f"DEBUG: Is it valid right now? {is_valid_now}")
    print("="*50 + "\n")
    # =====================================================

    frontend_url = "https://travel-sync-website-hsng.vercel.app"
    reset_link = f"{frontend_url}/reset-password/{uidb64}/{token}"    
    # Send Email
    subject = "Reset your TravelSync Password"
    message = f"Hi {user.username},\n\nClick the link below to reset your password:\n{reset_link}"
    
    try:
        send_mail(subject, message, settings.EMAIL_HOST_USER, [email], fail_silently=False)
        return Response({'message': 'Password reset link sent to your email.'}, status=status.HTTP_200_OK)
    except Exception as e:
        print("EMAIL ERROR:", e)
        return Response({'error': 'Failed to send email.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['PATCH'])
@permission_classes([AllowAny])
def reset_password_confirm(request):
    serializer = SetNewPasswordSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({'message': 'Password reset successfully'}, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ==========================================
# 4. REMOVED NOTIFICATIONS
# ==========================================

# ==========================================
# 5. WALLET MANAGEMENT (TRAVELCOINS)
# ==========================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_wallet_balance(request):
    try:
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        # Fetch the 10 most recent transactions
        transactions = wallet.transactions.all().order_by('-created_at')[:10]
        tx_data = []
        for tx in transactions:
            tx_data.append({
                "id": tx.id,
                "amount": str(tx.amount),
                "description": tx.description,
                "date": tx.created_at.strftime("%Y-%m-%d %H:%M")
            })

        return Response({
            "balance": str(wallet.balance),
            "transactions": tx_data
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

import razorpay
from decouple import config
from decimal import Decimal

RAZORPAY_KEY_ID = config('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = config('RAZORPAY_KEY_SECRET')
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_add_funds(request):
    data = request.data
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_signature = data.get('razorpay_signature')
    amount_in_rupees = data.get('amount') # This is the Rupee amount added

    params_dict = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature
    }

    try:
        # Verify Razorpay signature
        client.utility.verify_payment_signature(params_dict)

        wallet, created = Wallet.objects.get_or_create(user=request.user)
        added_amount = Decimal(str(amount_in_rupees))
        
        # Add to balance
        wallet.balance += added_amount
        wallet.save()

        # Log transaction
        WalletTransaction.objects.create(
            wallet=wallet,
            amount=added_amount,
            description="Added funds via Razorpay"
        )

        return Response({
            "message": f"Successfully added {added_amount} TravelCoins!",
            "new_balance": str(wallet.balance)
        }, status=status.HTTP_200_OK)

    except razorpay.errors.SignatureVerificationError:
        return Response({"error": "Payment Verification Failed"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
