from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from django.contrib.auth.models import User
from accounts.models import BusDetails
from routes.models import Route, Location, RouteTemplate
from bookings.models import Booking
from .models import Notice
from .serializers import (
    UserAdminSerializer,
    BusDetailsAdminSerializer,
    LocationAdminSerializer,
    RouteAdminSerializer,
    RouteTemplateAdminSerializer,
    BookingAdminSerializer,
    NoticeAdminSerializer
)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserAdminSerializer
    permission_classes = [IsAdminUser]

class BusDetailsViewSet(viewsets.ModelViewSet):
    queryset = BusDetails.objects.all().order_by('-id')
    serializer_class = BusDetailsAdminSerializer
    permission_classes = [IsAdminUser]

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

class NoticeViewSet(viewsets.ModelViewSet):
    queryset = Notice.objects.all().order_by('-created_at')
    serializer_class = NoticeAdminSerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
