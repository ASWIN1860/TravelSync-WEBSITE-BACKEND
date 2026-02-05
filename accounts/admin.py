from django.contrib import admin
from .models import BusDetails

@admin.register(BusDetails)
class BusDetailsAdmin(admin.ModelAdmin):
    list_display = ('bus_name', 'reg_number', 'user_email')
    
    def user_email(self, obj):
        return obj.user.email