from django.contrib import admin
from .models import Route, Trip, Location, RouteStop,TemplateStop,RouteTemplate

# 1. Allow adding Trips inside the Route page
class TripInline(admin.TabularInline):
    model = Trip
    extra = 1  # Show 1 empty slot by default

# 2. Allow adding Stops inside the Route page
class RouteStopInline(admin.TabularInline):
    model = RouteStop
    extra = 1
    ordering = ('stop_number',) # Keep them sorted 1, 2, 3...

# 3. The Main Route Admin
class RouteAdmin(admin.ModelAdmin):
    list_display = ('id', 'bus', 'start_location', 'end_location')
    inlines = [TripInline, RouteStopInline] 

# Register models
admin.site.register(Route, RouteAdmin)
admin.site.register(Location)
# We don't need to register Trip or RouteStop separately anymore because they are inside Route

class TemplateStopInline(admin.TabularInline):
    model = TemplateStop
    extra = 1
    ordering = ('stop_number',)

class RouteTemplateAdmin(admin.ModelAdmin):
    list_display = ('start_location', 'end_location')
    inlines = [TemplateStopInline]

admin.site.register(RouteTemplate, RouteTemplateAdmin)