from rest_framework import serializers
from .models import Route, Trip, RouteStop, RouteTemplate
import logging

logger = logging.getLogger(__name__)

class RouteStopSerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(source='location.name', read_only=True)
    
    class Meta:
        model = RouteStop
        fields = ['stop_number', 'location_name']

class TripSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = ['start_time', 'end_time']

class RouteSerializer(serializers.ModelSerializer):
    trips = TripSerializer(many=True)
    stops = serializers.ListField(child=serializers.DictField(), write_only=True, required=False)
    start_location_data = serializers.DictField(write_only=True, required=False)
    end_location_data = serializers.DictField(write_only=True, required=False)
    stop_list = RouteStopSerializer(source='stops', many=True, read_only=True)
    bus_name = serializers.CharField(source='bus.bus_name', read_only=True)
    
    # --- OPTIMIZATION: Get Status Directly ---
    is_booking_open = serializers.BooleanField(source='bus.is_booking_open', read_only=True)
    effective_status = serializers.ReadOnlyField()

    class Meta:
        model = Route
        fields = ['id', 'bus_name', 'start_location', 'end_location', 'via', 'trips', 'stops', 'stop_list', 'is_booking_open', 'effective_status', 'start_location_data', 'end_location_data']

    def create(self, validated_data):
        trips_data = validated_data.pop('trips')
        stops_data = validated_data.pop('stops', []) 
        start_loc_data = validated_data.pop('start_location_data', {})
        end_loc_data = validated_data.pop('end_location_data', {})
        
        start_name = validated_data.get('start_location')
        end_name = validated_data.get('end_location')
        via_name = validated_data.get('via')
        
        # 1. Ensure Start/End Locations exist in DB (for search ability)
        from .models import Location, RouteTemplate, TemplateStop 
        start_loc_obj, _ = Location.objects.get_or_create(name=start_name)
        if start_loc_data:
            start_loc_obj.latitude = start_loc_data.get('lat', start_loc_obj.latitude)
            start_loc_obj.longitude = start_loc_data.get('lon', start_loc_obj.longitude)
            start_loc_obj.district = start_loc_data.get('district', start_loc_obj.district)
            start_loc_obj.state = start_loc_data.get('state', start_loc_obj.state)
            start_loc_obj.save()

        end_loc_obj, _ = Location.objects.get_or_create(name=end_name)
        if end_loc_data:
            end_loc_obj.latitude = end_loc_data.get('lat', end_loc_obj.latitude)
            end_loc_obj.longitude = end_loc_data.get('lon', end_loc_obj.longitude)
            end_loc_obj.district = end_loc_data.get('district', end_loc_obj.district)
            end_loc_obj.state = end_loc_data.get('state', end_loc_obj.state)
            end_loc_obj.save()

        # Log the action (Info Level)
        logger.info(f"Creating Route: {start_name} -> {end_name} (Via: {via_name})")

        # 2. Create Route
        route = Route.objects.create(**validated_data)

        # 3. Create Trips
        for trip in trips_data:
            Trip.objects.create(route=route, **trip)

        # 4. AUTO-ASSIGN STOPS (Business Logic)
        try:
            # A. Check Direct Match
            template = RouteTemplate.objects.get(
                start_location__name__iexact=start_name,
                end_location__name__iexact=end_name,
                via__iexact=via_name 
            )
            logger.info(f"Found Template ID {template.id}. Copying stops...")
            
            stops = template.stops.all()
            for t_stop in stops:
                RouteStop.objects.create(route=route, location=t_stop.location, stop_number=t_stop.stop_number)

        except RouteTemplate.DoesNotExist:
            logger.info("Direct Template NOT found. Checking Reverse...")
            try:
                # B. Check Reverse Match
                reverse_template = RouteTemplate.objects.get(
                    start_location__name__iexact=end_name,
                    end_location__name__iexact=start_name,
                    via__iexact=via_name 
                )
                logger.info(f"Found Reverse Template ID {reverse_template.id}. Reversing stops...")
                
                original_stops = list(reverse_template.stops.all())
                # Assign stops in reverse order
                for index, t_stop in enumerate(reversed(original_stops)):
                    RouteStop.objects.create(route=route, location=t_stop.location, stop_number=index + 1)

            except RouteTemplate.DoesNotExist:
                # C. NO TEMPLATE FOUND -> CREATE NEW ONE (LEARNING)
                logger.info(f"No template found. Learning new route: {start_name} -> {end_name}")
                
                # Determine the user creating the template
                bus_details = validated_data.get('bus')
                creator_user = bus_details.user if bus_details else None

                # Always create a new template for this path
                new_template = RouteTemplate.objects.create(
                    start_location=start_loc_obj,
                    end_location=end_loc_obj,
                    via=via_name,
                    created_by=creator_user
                )
                
                if stops_data:
                    for index, stop_info in enumerate(stops_data):
                        # Get/Create Location for Stop
                        stop_name = stop_info.get('name')
                        if not stop_name: continue
                        loc_obj, _ = Location.objects.get_or_create(name=stop_name)
                        
                        loc_obj.latitude = stop_info.get('lat', loc_obj.latitude)
                        loc_obj.longitude = stop_info.get('lon', loc_obj.longitude)
                        loc_obj.district = stop_info.get('district', loc_obj.district)
                        loc_obj.state = stop_info.get('state', loc_obj.state)
                        loc_obj.save()
                        
                        # Create RouteStop (For this specific bus route)
                        RouteStop.objects.create(route=route, location=loc_obj, stop_number=index + 1)
                        
                        # Create TemplateStop (For future re-use)
                        TemplateStop.objects.create(template=new_template, location=loc_obj, stop_number=index + 1)
                        
                logger.info(f"Created new RouteTemplate ID {new_template.id} with {len(stops_data)} stops.")

        return route