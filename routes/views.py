from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q

from .models import Route, Location, RouteTemplate
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

    # --- OPTIMIZATION: Use Q objects for single DB hit ---
    templates = RouteTemplate.objects.filter(
        Q(start_location__name__iexact=start_name, end_location__name__iexact=end_name) |
        Q(start_location__name__iexact=end_name, end_location__name__iexact=start_name)
    ).values_list('via', flat=True).distinct()

    valid_vias = [v for v in templates if v] # Filter out empty strings
    
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