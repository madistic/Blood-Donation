from rest_framework import serializers
from .models import Hospital, Stock, NotificationJob
from django.contrib.auth.models import User


class StockSerializer(serializers.ModelSerializer):
    """Serializer for blood stock information"""
    class Meta:
        model = Stock
        fields = ['bloodgroup', 'unit']


class HospitalSerializer(serializers.ModelSerializer):
    """Serializer for hospital information with distance"""
    distance = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    blood_stock = serializers.SerializerMethodField()
    
    class Meta:
        model = Hospital
        fields = [
            'id', 'name', 'address', 'city', 'state',
            'contact_phone', 'contact_email', 'emergency_contact',
            'latitude', 'longitude', 'distance', 'blood_stock',
            'blood_bank_available', 'is_partner'
        ]
    
    def get_blood_stock(self, obj):
        """Get blood stock information grouped by type"""
        stock_data = {}
        stocks = Stock.objects.all()
        
        for stock in stocks:
            stock_data[stock.bloodgroup] = {
                'units': stock.unit,
                'available': stock.unit > 0
            }
        
        return stock_data


class NotificationJobSerializer(serializers.ModelSerializer):
    """Serializer for notification job creation"""
    class Meta:
        model = NotificationJob
        fields = [
            'user_latitude', 'user_longitude', 'radius_km', 
            'notification_type'
        ]
    
    def validate_user_latitude(self, value):
        """Validate latitude range"""
        if not (-90 <= float(value) <= 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90")
        return value
    
    def validate_user_longitude(self, value):
        """Validate longitude range"""
        if not (-180 <= float(value) <= 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180")
        return value
    
    def validate_radius_km(self, value):
        """Validate radius range"""
        if not (1 <= value <= 100):
            raise serializers.ValidationError("Radius must be between 1 and 100 km")
        return value


class NotificationJobStatusSerializer(serializers.ModelSerializer):
    """Serializer for notification job status"""
    user = serializers.StringRelatedField()
    
    class Meta:
        model = NotificationJob
        fields = [
            'id', 'user', 'status', 'notification_type',
            'retry_count', 'error_message', 'created_at',
            'updated_at', 'completed_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']