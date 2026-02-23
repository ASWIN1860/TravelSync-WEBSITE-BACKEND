from rest_framework import serializers
from django.contrib.auth.models import User
from accounts.models import BusDetails
from routes.models import Route, Location, RouteTemplate
from bookings.models import Booking
from .models import Notice

class UserAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'is_staff', 'is_active', 'is_superuser', 'date_joined']
        read_only_fields = ['date_joined']

class BusDetailsAdminSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = BusDetails
        fields = '__all__'

class LocationAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = '__all__'

class RouteAdminSerializer(serializers.ModelSerializer):
    start_location_name = serializers.CharField(source='start_location', read_only=True)
    end_location_name = serializers.CharField(source='end_location', read_only=True)
    bus_name = serializers.CharField(source='bus.bus_name', read_only=True)
    intermediate_stops = serializers.SerializerMethodField()
    start_time = serializers.SerializerMethodField()
    end_time = serializers.SerializerMethodField()

    class Meta:
        model = Route
        fields = '__all__'

    def get_intermediate_stops(self, obj):
        stops = obj.stops.all().order_by('stop_number')
        return [stop.location.name for stop in stops]

    def get_start_time(self, obj):
        first_trip = obj.trips.first()
        return first_trip.start_time.strftime('%I:%M %p') if first_trip else '--'

    def get_end_time(self, obj):
        first_trip = obj.trips.first()
        return first_trip.end_time.strftime('%I:%M %p') if first_trip else '--'

class RouteTemplateAdminSerializer(serializers.ModelSerializer):
    start_location_name = serializers.CharField(source='start_location.name', read_only=True)
    end_location_name = serializers.CharField(source='end_location.name', read_only=True)
    creator_email = serializers.CharField(source='created_by.email', read_only=True)

    class Meta:
        model = RouteTemplate
        fields = '__all__'

class BookingAdminSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    bus_name = serializers.CharField(source='bus.bus_name', read_only=True)

    class Meta:
        model = Booking
        fields = '__all__'

class NoticeAdminSerializer(serializers.ModelSerializer):
    creator_name = serializers.CharField(source='created_by.username', read_only=True)
    specific_user_email = serializers.CharField(source='specific_user.email', read_only=True)

    class Meta:
        model = Notice
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at']
