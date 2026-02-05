from django.db import models
from accounts.models import User, BusDetails
from routes.models import Route

class Booking(models.Model):
    ticket_id = models.CharField(max_length=20, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    # Critical Link: Validates against this specific bus
    bus = models.ForeignKey(BusDetails, on_delete=models.CASCADE) 
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    
    from_loc = models.CharField(max_length=100)
    to_loc = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.ticket_id} - {self.bus.bus_name}"