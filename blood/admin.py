from django.contrib import admin
from .models import Stock, BloodRequest, Certificate, Sponsor, Hospital, BloodCamp, CampRegistration, NotificationJob

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ['bloodgroup', 'unit']
    list_editable = ['unit']
    list_filter = ['bloodgroup']
    ordering = ['bloodgroup']

@admin.register(BloodRequest)
class BloodRequestAdmin(admin.ModelAdmin):
    list_display = ['patient_name', 'bloodgroup', 'unit', 'status', 'date']
    list_filter = ['status', 'bloodgroup', 'date']
    search_fields = ['patient_name']
    ordering = ['-date']

@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ['donor', 'certificate_type', 'donation_count', 'issued_date']
    list_filter = ['certificate_type', 'issued_date']
    search_fields = ['donor__user__first_name', 'donor__user__last_name']
    ordering = ['-issued_date']

@admin.register(Sponsor)
class SponsorAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'state', 'is_active']
    list_filter = ['is_active', 'state']
    search_fields = ['name', 'city']
    ordering = ['name']

@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'state', 'is_partner', 'blood_bank_available', 'has_coordinates']
    list_filter = ['is_partner', 'blood_bank_available', 'state']
    search_fields = ['name', 'city']
    ordering = ['name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'address', 'city', 'state')
        }),
        ('Contact Information', {
            'fields': ('contact_phone', 'contact_email', 'emergency_contact')
        }),
        ('Location Coordinates', {
            'fields': ('latitude', 'longitude'),
            'description': 'Enter precise coordinates for location-based services. Use decimal degrees format (e.g., 28.6139 for latitude, 77.2090 for longitude).'
        }),
        ('Services', {
            'fields': ('blood_bank_available', 'is_partner')
        }),
    )
    
    def has_coordinates(self, obj):
        return obj.has_coordinates
    has_coordinates.boolean = True
    has_coordinates.short_description = 'Has Coordinates'

@admin.register(BloodCamp)
class BloodCampAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'city', 'status', 'registered_donors', 'target_donors']
    list_filter = ['status', 'start_date', 'state']
    search_fields = ['name', 'city']
    ordering = ['-start_date']

@admin.register(CampRegistration)
class CampRegistrationAdmin(admin.ModelAdmin):
    list_display = ['donor', 'camp', 'registered_date', 'attended', 'donated']
    list_filter = ['attended', 'donated', 'registered_date']
    search_fields = ['donor__user__first_name', 'donor__user__last_name', 'camp__name']
    ordering = ['-registered_date']

@admin.register(NotificationJob)
class NotificationJobAdmin(admin.ModelAdmin):
    list_display = ['user', 'status', 'notification_type', 'radius_km', 'retry_count', 'created_at']
    list_filter = ['status', 'notification_type', 'created_at']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at', 'completed_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Request Information', {
            'fields': ('user', 'user_latitude', 'user_longitude', 'radius_km', 'notification_type')
        }),
        ('Status & Tracking', {
            'fields': ('status', 'retry_count', 'max_retries', 'error_message')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )