from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def api_root(request):
    return JsonResponse({"message": "Hello from TravelSync Backend!"})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api_root),
    
    # --- CHANGED: Standardized to 'api/accounts/' ---
    path('api/accounts/', include('accounts.urls')), 
    
    path('api/routes/', include('routes.urls')),
    path('api/bookings/', include('bookings.urls')),

    path('api/chatbot/', include('chatbot.urls')),
    
    # Admin Panel APIs
    path('api/admin/', include('admin_panel.urls')),
]