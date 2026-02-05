from django.contrib import admin
from .models import Booking

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('ticket_id', 'bus', 'from_loc', 'to_loc', 'price', 'is_verified', 'created_at')
    list_filter = ('is_verified', 'created_at')
    search_fields = ('ticket_id', 'bus__bus_name')