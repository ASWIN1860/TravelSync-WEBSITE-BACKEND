from django.contrib import admin
from .models import BusDetails, Wallet, WalletTransaction

@admin.register(BusDetails)
class BusDetailsAdmin(admin.ModelAdmin):
    list_display = ('bus_name', 'reg_number', 'user_email')
    
    def user_email(self, obj):
        return obj.user.email

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'updated_at')
    search_fields = ('user__username', 'user__email')

@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'amount', 'description', 'created_at')
    search_fields = ('wallet__user__username', 'description')
    list_filter = ('created_at',)