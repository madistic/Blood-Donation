from django.urls import path
from . import api_views

app_name = 'blood_api'

urlpatterns = [
    # Hospital location APIs
    path('nearby-hospitals/', api_views.nearby_hospitals, name='nearby_hospitals'),
    path('blood-stock/', api_views.blood_stock_summary, name='blood_stock_summary'),
    
    # Notification APIs
    path('notify-hospitals/', api_views.notify_hospitals, name='notify_hospitals'),
    path('notification-status/<int:job_id>/', api_views.notification_status, name='notification_status'),
    
    # Staff APIs
    path('hospitals/<int:hospital_id>/update-stock/', api_views.update_hospital_stock, name='update_hospital_stock'),
]