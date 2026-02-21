from django.urls import path
from . import views

urlpatterns = [
    path('add/', views.add_route, name='add_route'),
    path('get/', views.get_routes, name='get_routes'),
    path('search/', views.search_routes, name='search_routes'),
    path('suggestions/', views.get_location_suggestions, name='suggestions'),
    path('template-vias/', views.get_template_vias, name='get_template_vias'),
    path('delete/<int:route_id>/', views.delete_route, name='delete_route'),
    path('toggle-route-status/', views.toggle_route_status, name='toggle_route_status'),
    path('toggle-favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('my-favorites/', views.my_favorites, name='my_favorites'),
]