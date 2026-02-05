from django.db import models
from django.contrib.auth.models import User

class BusDetails(models.Model):
    # Existing Fields
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='bus_details')
    bus_name = models.CharField(max_length=100)
    reg_number = models.CharField(max_length=50)
    
    # --- NEW FIELDS FOR PAYMENTS ---
    # Stores the bus type (e.g., "AC", "Non-AC") - Optional but good for UI
    bus_type = models.CharField(max_length=50, default="Standard", blank=True) 
    
    # The Operator's UPI ID (e.g., "mybus@okicici")
    upi_id = models.CharField(max_length=50, blank=True, null=True) 
    
    # Wallet to track earnings
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) 

    is_booking_open = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.bus_name} ({self.user.username})"