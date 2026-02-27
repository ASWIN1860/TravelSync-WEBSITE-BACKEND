from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from django.contrib.auth.models import User
from accounts.models import BusDetails
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
    BookingAdminSerializer
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
