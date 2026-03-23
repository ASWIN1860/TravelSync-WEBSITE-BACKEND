from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.contrib.auth.models import User
from accounts.models import BusDetails, WithdrawalRequest, Wallet
from django.db.models import Sum
from routes.models import Route, Location, RouteTemplate
from bookings.models import Booking
from django.core.mail import send_mail
from django.conf import settings
from .serializers import (
    UserAdminSerializer,
    BusDetailsAdminSerializer,
    LocationAdminSerializer,
    RouteAdminSerializer,
    RouteTemplateAdminSerializer,
    BookingAdminSerializer,
    WithdrawalRequestAdminSerializer
)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserAdminSerializer
    permission_classes = [IsAdminUser]

class BusDetailsViewSet(viewsets.ModelViewSet):
    queryset = BusDetails.objects.all().order_by('-id')
    serializer_class = BusDetailsAdminSerializer
    permission_classes = [IsAdminUser]

    def perform_update(self, serializer):
        instance = self.get_object()
        old_status = instance.status
        updated_instance = serializer.save()
        
        if old_status != 'approved' and updated_instance.status == 'approved':
            try:
                user_email = updated_instance.user.email
                username = updated_instance.user.username
                bus_name = updated_instance.bus_name
                
                subject = "Bus Registration Approved - TravelSync"
                message = f"Hello {username},\n\nYour bus registration for '{bus_name}' has been approved by the admin! You can now log in to the TravelSync bus operator panel.\n\nThank you,\nTravelSync Team"
                
                send_mail(subject, message, settings.EMAIL_HOST_USER, [user_email], fail_silently=True)
            except Exception as e:
                print(f"Failed to send approval email: {e}")

class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all().order_by('name')
    serializer_class = LocationAdminSerializer
    permission_classes = [IsAdminUser]

class RouteViewSet(viewsets.ModelViewSet):
    queryset = Route.objects.all().order_by('-id')
    serializer_class = RouteAdminSerializer
    permission_classes = [IsAdminUser]

class RouteTemplateViewSet(viewsets.ModelViewSet):
    queryset = RouteTemplate.objects.all().order_by('-id')
    serializer_class = RouteTemplateAdminSerializer
    permission_classes = [IsAdminUser]

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all().order_by('-created_at')
    serializer_class = BookingAdminSerializer
    permission_classes = [IsAdminUser]

class WithdrawalRequestViewSet(viewsets.ModelViewSet):
    queryset = WithdrawalRequest.objects.all().order_by('-created_at')
    serializer_class = WithdrawalRequestAdminSerializer
    permission_classes = [IsAdminUser]

    def perform_update(self, serializer):
        instance = self.get_object()
        old_status = instance.status
        updated_instance = serializer.save()

        # If Admin REJECTS, refund the TC back to the operator
        if old_status == 'pending' and updated_instance.status == 'rejected':
            from django.db.models import F
            try:
                bus = BusDetails.objects.get(user=updated_instance.user)
                bus.total_earnings = F('total_earnings') + updated_instance.amount
                bus.save()
            except BusDetails.DoesNotExist:
                pass

@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_platform_balance(request):
    try:
        total_wallets = Wallet.objects.aggregate(Sum('balance'))['balance__sum'] or 0
        total_earnings = BusDetails.objects.aggregate(Sum('total_earnings'))['total_earnings__sum'] or 0
        total_pending_withdrawals = WithdrawalRequest.objects.filter(status='pending').aggregate(Sum('amount'))['amount__sum'] or 0
        
        total_held_funds = total_wallets + total_earnings + total_pending_withdrawals
        
        return Response({
            "total_platform_revenue": str(total_held_funds)
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
