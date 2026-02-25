from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet,
    BusDetailsViewSet,
    LocationViewSet,
    RouteViewSet,
    RouteTemplateViewSet,
    BookingViewSet
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='admin-user')
router.register(r'buses', BusDetailsViewSet, basename='admin-bus')
router.register(r'locations', LocationViewSet, basename='admin-location')
router.register(r'routes', RouteViewSet, basename='admin-route')
router.register(r'templates', RouteTemplateViewSet, basename='admin-template')
router.register(r'bookings', BookingViewSet, basename='admin-booking')

urlpatterns = [
    path('', include(router.urls)),
]
