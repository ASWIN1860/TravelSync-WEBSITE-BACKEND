from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q

from .models import Route, Location, RouteTemplate, FavoriteRoute, RouteNotification
from accounts.models import BusDetails
from .serializers import RouteSerializer

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_route(request):
    try:
        bus_details = BusDetails.objects.get(user=request.user)
    except BusDetails.DoesNotExist:
        return Response({"error": "You are not registered as a bus operator."}, status=status.HTTP_403_FORBIDDEN)

    serializer = RouteSerializer(data=request.data)
    
    if serializer.is_valid():
        serializer.save(bus=bus_details)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_routes(request):
    try:
        bus_details = BusDetails.objects.get(user=request.user)
    except BusDetails.DoesNotExist:
        return Response({"error": "Not a bus operator"}, status=status.HTTP_403_FORBIDDEN)

    routes = Route.objects.filter(bus=bus_details)
    serializer = RouteSerializer(routes, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def search_routes(request):
    from_query = request.GET.get('from', '').strip()
    to_query = request.GET.get('to', '').strip()

    if not from_query or not to_query:
        return Response({"error": "Please provide start and end locations"}, status=status.HTTP_400_BAD_REQUEST)

    # 1. Filter candidates from DB (Efficient Filtering)
    from_matches = Route.objects.filter(
        Q(start_location__icontains=from_query) |
        Q(stops__location__name__icontains=from_query) 
    ).distinct()

    to_matches = Route.objects.filter(
        Q(end_location__icontains=to_query) |
        Q(stops__location__name__icontains=to_query)
    ).distinct()

    # Intersect
    candidate_routes = from_matches & to_matches
    # Prefetch related data to avoid N+1 problem during serialization
    candidate_routes = candidate_routes.distinct().prefetch_related('stops__location', 'bus')

    valid_routes = []

    # 2. Logic Check: Does Start come BEFORE End?
    for route in candidate_routes:
        start_index = -1
        end_index = -1

        # Determine Start Index
        if from_query.lower() in route.start_location.lower():
            start_index = 0
        else:
            for stop in route.stops.all():
                if from_query.lower() in stop.location.name.lower():
                    start_index = stop.stop_number
                    break 
        
        # Determine End Index
        if to_query.lower() in route.end_location.lower():
            end_index = 9999
        else:
            for stop in route.stops.all():
                if to_query.lower() in stop.location.name.lower():
                    end_index = stop.stop_number
                    break 

        if start_index != -1 and end_index != -1 and start_index < end_index:
            valid_routes.append(route)

    # --- OPTIMIZATION: REMOVED MANUAL LOOP ---
    # The Serializer now automatically handles 'is_booking_open'
    serializer = RouteSerializer(valid_routes, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_location_suggestions(request):
    query = request.GET.get('q', '')
    
    if len(query) < 1:
        return Response([])

    locations = Location.objects.filter(name__icontains=query)[:10]
    data = [loc.name for loc in locations]
    
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated]) 
def get_template_vias(request):
    """
    OPTIMIZED: Fetches both forward and reverse templates in a SINGLE database query.
    """
    start_name = request.GET.get('start', '')
    end_name = request.GET.get('end', '')

    if not start_name or not end_name:
        return Response([])

    # --- FIXED: Return objects with via and stops ---
    templates = RouteTemplate.objects.filter(
        Q(start_location__name__iexact=start_name, end_location__name__iexact=end_name) |
        Q(start_location__name__iexact=end_name, end_location__name__iexact=start_name)
    ).prefetch_related('stops__location').distinct()

    valid_vias = []
    seen_vias = set()

    for t in templates:
        if not t.via or t.via in seen_vias:
            continue
        seen_vias.add(t.via)
        
        # Order the stops by stop_number
        sorted_stops = sorted(t.stops.all(), key=lambda x: x.stop_number)
        stop_names = [stop.location.name for stop in sorted_stops]
        
        # Check if we queried in reverse order of the stored template
        if t.end_location.name.lower() == start_name.lower() and t.start_location.name.lower() == end_name.lower():
            stop_names.reverse()
            
        valid_vias.append({
            "via": t.via,
            "stops": stop_names
        })
    
    return Response(valid_vias)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_route(request, route_id):
    try:
        bus_details = BusDetails.objects.get(user=request.user)
        route = Route.objects.get(id=route_id, bus=bus_details)
        route.delete()
        return Response({"message": "Route deleted successfully"}, status=status.HTTP_200_OK)

    except BusDetails.DoesNotExist:
        return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)
    except Route.DoesNotExist:
        return Response({"error": "Route not found or access denied"}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_favorite(request):
    route_id = request.data.get('route_id')
    if not route_id:
        return Response({"error": "route_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        route = Route.objects.get(id=route_id)
    except Route.DoesNotExist:
        return Response({"error": "Route not found"}, status=status.HTTP_404_NOT_FOUND)

    favorite, created = FavoriteRoute.objects.get_or_create(user=request.user, route=route)
    
    if not created:
        favorite.delete()
        return Response({"message": "Route removed from favorites", "is_favorite": False}, status=status.HTTP_200_OK)
        
    return Response({"message": "Route added to favorites", "is_favorite": True}, status=status.HTTP_201_CREATED)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def toggle_route_status(request):
    try:
        bus_details = BusDetails.objects.get(user=request.user)
    except BusDetails.DoesNotExist:
        return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

    route_id = request.data.get('route_id')
    new_status = request.data.get('status')

    if not route_id or not new_status:
        return Response({"error": "route_id and status are required"}, status=status.HTTP_400_BAD_REQUEST)

    if new_status not in ['active', 'closed_today', 'closed_permanently']:
        return Response({"error": "Invalid status type"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        route = Route.objects.get(id=route_id, bus=bus_details)
        route.status = new_status
        route.save(update_fields=['status', 'status_updated_at']) # auto_now handles the timestamp
        return Response({"message": f"Route status updated to {new_status}", "effective_status": route.effective_status}, status=status.HTTP_200_OK)
    except Route.DoesNotExist:
        return Response({"error": "Route not found or access denied"}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_favorites(request):
    favorites = FavoriteRoute.objects.filter(user=request.user).select_related('route', 'route__bus').prefetch_related('route__stops__location', 'route__trips')
    routes = [fav.route for fav in favorites]
    serializer = RouteSerializer(routes, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_route_notification(request):
    route_id = request.data.get('route_id')
    stop_name = request.data.get('stop_name')
    notify_minutes = request.data.get('notify_minutes')

    if not all([route_id, stop_name, notify_minutes]):
        return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        route = Route.objects.get(id=route_id)
        # Create or Update the notification preference for this user+route+stop combo
        notification, created = RouteNotification.objects.update_or_create(
            user=request.user,
            route=route,
            stop_name=stop_name,
            defaults={'notify_minutes': int(notify_minutes)}
        )
        msg = "Notification preference saved!" if created else "Notification preference updated!"
        return Response({"message": msg}, status=status.HTTP_200_OK)
    except Route.DoesNotExist:
        return Response({"error": "Route not found"}, status=status.HTTP_404_NOT_FOUND)
    except ValueError:
        return Response({"error": "Invalid notify_minutes value"}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_live_location(request, route_id):
    try:
        route = Route.objects.select_related('bus').get(id=route_id)
        bus = route.bus
        
        if not bus.current_lat or not bus.current_lng:
            return Response({"error": "Live location not available"}, status=status.HTTP_404_NOT_FOUND)
            
        return Response({
            "lat": bus.current_lat,
            "lng": bus.current_lng,
            "last_updated": bus.last_updated_location
        })
    except Route.DoesNotExist:
        return Response({"error": "Route not found"}, status=status.HTTP_404_NOT_FOUND)
