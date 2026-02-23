from django.db import models
from django.contrib.auth.models import User

class Notice(models.Model):
    TARGET_CHOICES = [
        ('all_bus_operators', 'All Bus Operators'),
        ('all_passengers', 'All Passengers/Users'),
        ('all_users', 'All Users'),
        ('specific_user', 'Specific User')
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    target_audience = models.CharField(max_length=50, choices=TARGET_CHOICES, default='all_users')
    specific_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='received_notices')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_notices')

    def __str__(self):
        return self.title
