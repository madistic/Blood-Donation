from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Q
from decimal import Decimal
import json
import logging

from .models import Hospital, Stock, NotificationJob
from .serializers import HospitalSerializer, NotificationJobSerializer
from .tasks import send_hospital_notifications

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@cache_page(60 * 5)  # Cache for 5 minutes
def nearby_hospitals(request):
    """
    API endpoint to find nearby hospitals within a specified radius
    
    Query Parameters:
    - lat: User latitude (required)
    - lng: User longitude (required) 
    - radius_km: Search radius in kilometers (optional, default: 10)
    
    Returns:
    - List of hospitals sorted by distance
    - Blood stock information for each hospital
    - Distance from user location
    - Last updated timestamp
    """
    try:
        # Get and validate parameters
        user_lat = request.GET.get('lat')
        user_lng = request.GET.get('lng')
        radius_km = int(request.GET.get('radius_km', 10))
        
        if not user_lat or not user_lng:
            return Response({
                'error': 'Latitude and longitude are required',
                'code': 'MISSING_COORDINATES'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user_lat = Decimal(str(user_lat))
            user_lng = Decimal(str(user_lng))
        except (ValueError, TypeError):
            return Response({
                'error': 'Invalid latitude or longitude format',
                'code': 'INVALID_COORDINATES'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate coordinate ranges
        if not (-90 <= user_lat <= 90):
            return Response({
                'error': 'Latitude must be between -90 and 90',
                'code': 'INVALID_LATITUDE'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        if not (-180 <= user_lng <= 180):
            return Response({
                'error': 'Longitude must be between -180 and 180',
                'code': 'INVALID_LONGITUDE'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not (1 <= radius_km <= 100):
            return Response({
                'error': 'Radius must be between 1 and 100 km',
                'code': 'INVALID_RADIUS'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get hospitals with coordinates
        hospitals = Hospital.objects.filter(
            is_partner=True,
            latitude__isnull=False,
            longitude__isnull=False
        )
        
        # Calculate distances and filter by radius
        nearby_hospitals = []
        for hospital in hospitals:
            distance = hospital.calculate_distance(user_lat, user_lng)
            if distance is not None and distance <= radius_km:
                hospital.distance = round(distance, 2)
                nearby_hospitals.append(hospital)
        
        # Sort by distance
        nearby_hospitals.sort(key=lambda h: h.distance)
        
        # Serialize data
        serializer = HospitalSerializer(nearby_hospitals, many=True)
        
        # Get last stock update time
        last_stock_update = Stock.objects.order_by('-id').first()
        last_updated = last_stock_update.id if last_stock_update else None
        
        return Response({
            'hospitals': serializer.data,
            'total_found': len(nearby_hospitals),
            'search_radius_km': radius_km,
            'user_coordinates': {
                'latitude': float(user_lat),
                'longitude': float(user_lng)
            },
            'last_updated': timezone.now().isoformat(),
            'stock_last_updated': last_updated
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in nearby_hospitals API: {str(e)}")
        return Response({
            'error': 'Internal server error',
            'code': 'SERVER_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notify_hospitals(request):
    """
    API endpoint to request hospital notifications via SMS and Email
    
    Request Body:
    - user_latitude: User latitude
    - user_longitude: User longitude
    - radius_km: Search radius (optional, default: 10)
    - notification_type: 'SMS', 'EMAIL', or 'BOTH' (optional, default: 'BOTH')
    
    Returns:
    - Notification job ID
    - Status information
    """
    try:
        # Rate limiting check (max 5 requests per hour per user)
        cache_key = f"notification_rate_limit_{request.user.id}"
        current_requests = cache.get(cache_key, 0)
        
        if current_requests >= 5:
            return Response({
                'error': 'Rate limit exceeded. Maximum 5 notification requests per hour.',
                'code': 'RATE_LIMIT_EXCEEDED'
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # Parse request data
        data = json.loads(request.body) if request.body else {}
        
        # Create serializer and validate
        serializer = NotificationJobSerializer(data=data)
        if not serializer.is_valid():
            return Response({
                'error': 'Invalid request data',
                'details': serializer.errors,
                'code': 'VALIDATION_ERROR'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create notification job
        notification_job = NotificationJob.objects.create(
            user=request.user,
            user_latitude=serializer.validated_data['user_latitude'],
            user_longitude=serializer.validated_data['user_longitude'],
            radius_km=serializer.validated_data.get('radius_km', 10),
            notification_type=serializer.validated_data.get('notification_type', 'BOTH')
        )
        
        # Increment rate limit counter
        cache.set(cache_key, current_requests + 1, 3600)  # 1 hour
        
        # Queue background task for sending notifications
        try:
            from .tasks import send_hospital_notifications
            send_hospital_notifications.delay(notification_job.id)
            
            return Response({
                'job_id': notification_job.id,
                'status': 'queued',
                'message': 'Notification request queued successfully',
                'estimated_delivery': '2-5 minutes'
            }, status=status.HTTP_201_CREATED)
            
        except ImportError:
            # Fallback if Celery is not available - process synchronously
            logger.warning("Celery not available, processing notification synchronously")
            from .tasks import process_notification_sync
            result = process_notification_sync(notification_job.id)
            
            return Response({
                'job_id': notification_job.id,
                'status': 'completed' if result else 'failed',
                'message': 'Notification processed',
                'processed_synchronously': True
            }, status=status.HTTP_201_CREATED)
        
    except json.JSONDecodeError:
        return Response({
            'error': 'Invalid JSON in request body',
            'code': 'INVALID_JSON'
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Error in notify_hospitals API: {str(e)}")
        return Response({
            'error': 'Internal server error',
            'code': 'SERVER_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_status(request, job_id):
    """
    API endpoint to check notification job status
    
    Returns:
    - Job status and details
    - Error information if failed
    """
    try:
        notification_job = NotificationJob.objects.get(
            id=job_id, 
            user=request.user
        )
        
        from .serializers import NotificationJobStatusSerializer
        serializer = NotificationJobStatusSerializer(notification_job)
        
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except NotificationJob.DoesNotExist:
        return Response({
            'error': 'Notification job not found',
            'code': 'JOB_NOT_FOUND'
        }, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        logger.error(f"Error in notification_status API: {str(e)}")
        return Response({
            'error': 'Internal server error',
            'code': 'SERVER_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def blood_stock_summary(request):
    """
    API endpoint to get current blood stock summary
    
    Returns:
    - Blood stock by type
    - Total units available
    - Last updated timestamp
    """
    try:
        stocks = Stock.objects.all()
        stock_data = {}
        total_units = 0
        
        for stock in stocks:
            stock_data[stock.bloodgroup] = {
                'units': stock.unit,
                'available': stock.unit > 0,
                'status': 'available' if stock.unit > 10 else 'low' if stock.unit > 0 else 'unavailable'
            }
            total_units += stock.unit
        
        return Response({
            'blood_stock': stock_data,
            'total_units': total_units,
            'last_updated': timezone.now().isoformat(),
            'blood_types_count': len(stock_data)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in blood_stock_summary API: {str(e)}")
        return Response({
            'error': 'Internal server error',
            'code': 'SERVER_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Admin API endpoints for staff
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_hospital_stock(request, hospital_id):
    """
    Staff endpoint to update blood stock for a specific hospital
    Note: This is a simplified version - in production you'd want 
    hospital-specific stock tracking
    """
    if not request.user.is_staff:
        return Response({
            'error': 'Staff access required',
            'code': 'PERMISSION_DENIED'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        hospital = Hospital.objects.get(id=hospital_id)
        data = json.loads(request.body)
        
        # Update stock (simplified - updates global stock)
        blood_group = data.get('blood_group')
        units = data.get('units')
        
        if not blood_group or units is None:
            return Response({
                'error': 'blood_group and units are required',
                'code': 'MISSING_FIELDS'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        stock, created = Stock.objects.get_or_create(
            bloodgroup=blood_group,
            defaults={'unit': 0}
        )
        stock.unit = max(0, int(units))  # Ensure non-negative
        stock.save()
        
        return Response({
            'message': f'Stock updated for {hospital.name}',
            'blood_group': blood_group,
            'new_units': stock.unit
        }, status=status.HTTP_200_OK)
        
    except Hospital.DoesNotExist:
        return Response({
            'error': 'Hospital not found',
            'code': 'HOSPITAL_NOT_FOUND'
        }, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        logger.error(f"Error updating hospital stock: {str(e)}")
        return Response({
            'error': 'Internal server error',
            'code': 'SERVER_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)