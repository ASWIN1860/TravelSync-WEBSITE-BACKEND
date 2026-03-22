from django.urls import path
from . import views

urlpatterns = [
    # Payment Flow
    path('initiate-payment/', views.initiate_payment, name='initiate_payment'),
    path('verify-payment/', views.verify_payment, name='verify_payment'),
    path('pay-with-wallet/', views.pay_with_wallet, name='pay_with_wallet'),
    
    # Operator Verification (Scanning)
    path('verify/', views.verify_ticket, name='verify_ticket'),
    
    # User Tickets
    path('my-tickets/', views.get_user_tickets, name='get_user_tickets'),

    # Operator Functions
    path('withdraw-funds/', views.withdraw_funds, name='withdraw_funds'),
    path('withdraw-history/', views.get_withdraw_history, name='get_withdraw_history'),
]