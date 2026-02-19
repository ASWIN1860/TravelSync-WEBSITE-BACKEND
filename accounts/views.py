from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes 
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from .serializers import RegisterSerializer, UserSerializer, BusRegisterSerializer, SetNewPasswordSerializer
from .models import BusDetails 
import logging
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.core.mail import send_mail
from django.conf import settings
from .tokens import custom_token_generator # <--- CRITICAL IMPORT

logger = logging.getLogger(__name__)

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
        bus_details = serializer.save()
        user = bus_details.user
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            "user": UserSerializer(user).data,
            "token": token.key,
            "role": "bus",
            "message": "Bus Registered successfully"
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
            is_bus_operator = hasattr(user, 'bus_details') 
            role = "bus" if is_bus_operator else "user"

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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_bus_profile(request):
    try:
        bus = BusDetails.objects.get(user=request.user)
        return Response({
            "upi_id": bus.upi_id,
            "total_earnings": bus.total_earnings,
            "is_booking_open": bus.is_booking_open, 
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

    reset_link = f"http://localhost:5173/reset-password/{uidb64}/{token}"
    
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