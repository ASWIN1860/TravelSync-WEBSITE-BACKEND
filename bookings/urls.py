from django.urls import path
from . import views

urlpatterns = [
    # Payment Flow
    path('initiate-payment/', views.initiate_payment, name='initiate_payment'),
    path('verify-payment/', views.verify_payment, name='verify_payment'),
    
    # Operator Verification (Scanning)
    path('verify/', views.verify_ticket, name='verify_ticket'),
    
    # User Tickets
    path('my-tickets/', views.get_user_tickets, name='get_user_tickets'),
]