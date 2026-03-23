from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
class BusDetails(models.Model):
    # Existing Fields
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='bus_details')
    bus_name = models.CharField(max_length=100)
    reg_number = models.CharField(max_length=50)
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='approved')
    
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)  


    # --- NEW FIELDS FOR PAYMENTS ---
    # Stores the bus type (e.g., "AC", "Non-AC") - Optional but good for UI
    bus_type = models.CharField(max_length=50, default="Standard", blank=True) 
    
    # The Operator's UPI ID (e.g., "mybus@okicici")
    upi_id = models.CharField(max_length=50, blank=True, null=True) 
    
    # Wallet to track earnings
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) 

    # Crowd Control Status (green=low, yellow=medium, red=overcrowded)
    CROWD_CHOICES = (
        ('green', 'Green'),
        ('yellow', 'Yellow'),
        ('red', 'Red'),
    )
    crowd_status = models.CharField(max_length=10, choices=CROWD_CHOICES, default='green')

    is_booking_open = models.BooleanField(default=False)


    def __str__(self):
        return f"{self.bus_name} ({self.user.username})"

# ==========================================
#  TRAVELCOIN WALLET SYSTEM
# ==========================================

class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) # TravelCoins (1 Coin = 1 Rupee)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Wallet - {self.balance} TC"

class WalletTransaction(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2) # Positive for add, Negative for spend
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.wallet.user.username} | {self.amount} TC | {self.description}"

# Signal to auto-create wallet for new users
@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(user=instance)

class WithdrawalRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    account_name = models.CharField(max_length=255)
    bank_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=50)
    ifsc_code = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Withdrawal by {self.user.username} for {self.amount} TC ({self.status})"
