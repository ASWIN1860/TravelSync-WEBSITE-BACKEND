from django.urls import path
from . import views

urlpatterns = [
    # Auth Endpoints
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.login_view, name='login'),
    
    # --- NEW: Get Current User (For Header) ---
    path('me/', views.get_current_user, name='get_current_user'),
    # ------------------------------------------

    # Bus Operator Endpoints
    path('register-bus/', views.register_bus_view, name='register_bus'),
    path('profile/', views.get_bus_profile, name='get_bus_profile'),
    path('update-upi/', views.update_upi, name='update_upi'),
    path('toggle-status/', views.toggle_booking_status, name='toggle_booking_status'),
]