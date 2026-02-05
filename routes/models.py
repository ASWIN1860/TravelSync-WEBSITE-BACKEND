from django.db import models
from accounts.models import BusDetails  

class Location(models.Model):
    name = models.CharField(max_length=100, unique=True) # unique=True 

    def __str__(self):
        return self.name

class Route(models.Model):
    bus = models.ForeignKey(BusDetails, on_delete=models.CASCADE, related_name='routes')
    start_location = models.CharField(max_length=100)
    end_location = models.CharField(max_length=100)
    via = models.CharField(max_length=100, blank=True, null=True) 
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.bus.bus_name}: {self.start_location} -> {self.end_location}"
    

class RouteStop(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='stops')
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    stop_number = models.PositiveIntegerField()
    # arrival_time_offset = models.IntegerField(help_text="Minutes from start")

    class Meta:
        ordering = ['stop_number'] 
        
    def __str__(self):
        return f"{self.route.id} - Stop {self.stop_number}: {self.location.name}"

class Trip(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='trips')
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    def __str__(self):
        return f"{self.route.start_location} ({self.start_time})"


class RouteTemplate(models.Model):
    start_location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='templates_start')
    end_location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='templates_end')
    via = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. Civil Station, Medical College") # <--- NEW FIELD
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"TEMPLATE: {self.start_location} -> {self.end_location} ({self.via})"
    
    
class TemplateStop(models.Model):
    template = models.ForeignKey(RouteTemplate, on_delete=models.CASCADE, related_name='stops')
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    stop_number = models.PositiveIntegerField()

    class Meta:
        ordering = ['stop_number']

    def __str__(self):
        return f"{self.template} - {self.stop_number}: {self.location}"