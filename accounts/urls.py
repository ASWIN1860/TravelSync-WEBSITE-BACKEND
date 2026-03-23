from django.urls import path
from . import views

urlpatterns = [
    # Auth Endpoints
    path('register/', views.RegisterView.as_view(), name='register'),
    path('check-availability/', views.check_availability, name='check_availability'),
    path('login/', views.login_view, name='login'),
    
    # --- NEW: Get Current User (For Header) ---
    path('me/', views.get_current_user, name='get_current_user'),
    # ------------------------------------------

    # Bus Operator Endpoints
    path('register-bus/', views.register_bus_view, name='register_bus'),
    path('profile/', views.get_bus_profile, name='get_bus_profile'),
    path('update-upi/', views.update_upi, name='update_upi'),
    path('toggle-status/', views.toggle_booking_status, name='toggle_booking_status'),
    path('update-crowd-status/', views.update_crowd_status, name='update_crowd_status'),
    path('forgot-password/', views.forgot_password_request, name='forgot-password'),
    path('reset-password-confirm/', views.reset_password_confirm, name='reset-password-confirm'),

    path('send-otp/', views.send_email_otp, name='send_email_otp'),
    path('verify-otp/', views.verify_email_otp, name='verify_email_otp'),
    
    # Wallet Enpoints
    path('wallet/', views.get_wallet_balance, name='get_wallet_balance'),
    path('wallet/verify-add-funds/', views.verify_add_funds, name='verify_add_funds'),
]