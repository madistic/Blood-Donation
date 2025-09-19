# Hospital Location & Notification System - Setup Guide

## 🎯 Overview
A comprehensive location-based hospital finder with SMS and email notification system has been added to your Blood Bank Management System. Users can find nearby hospitals, view blood stock availability, and receive notifications with hospital contact information.

## 🚀 Features Added

### 1. **Location-Based Hospital Search**
- Real-time geolocation using browser GPS
- Haversine distance calculation for accurate results
- Configurable search radius (1-100 km)
- Interactive map with hospital markers
- List view with detailed hospital information

### 2. **Hospital Coordinate System**
- Extended Hospital model with latitude/longitude fields
- Admin interface for coordinate management
- Coordinate validation and error handling
- Distance calculation methods

### 3. **Notification System**
- SMS notifications via Twilio
- Email notifications via SendGrid or Django email
- Background job processing with Celery
- Rate limiting to prevent abuse
- Retry logic with exponential backoff

### 4. **REST API Endpoints**
- `/api/nearby-hospitals/` - Find hospitals within radius
- `/api/notify-hospitals/` - Request notifications
- `/api/notification-status/<job_id>/` - Check notification status
- `/api/blood-stock/` - Get current blood stock summary

## 📁 Files Added/Modified

### Backend Files:
- `blood/models.py` - Added Hospital coordinates and NotificationJob model
- `blood/serializers.py` - API serializers for hospital and notification data
- `blood/api_views.py` - REST API endpoints
- `blood/api_urls.py` - API URL routing
- `blood/tasks.py` - Celery tasks for notifications
- `blood/admin.py` - Enhanced admin interface
- `blood/migrations/0006_add_hospital_coordinates.py` - Database migration

### Frontend Files:
- `static/js/hospital-location.js` - Location management and mapping
- `templates/blood/hospital_finder.html` - Hospital finder page
- `templates/blood/email/hospital_notification.html` - Email template

### Configuration Files:
- `bloodbankmanagement/celery.py` - Celery configuration
- `requirements.txt` - Added new dependencies
- `.env.example` - Added environment variables

### Test Files:
- `blood/tests/test_location_api.py` - API endpoint tests
- `blood/tests/test_notification_tasks.py` - Notification system tests

## 🔧 Setup Instructions

### 1. Install Dependencies
```bash
pip install djangorestframework==3.14.0 celery==5.3.4 redis==5.0.1 twilio==8.10.0 sendgrid==6.10.0
```

### 2. Run Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. Seed Hospital Coordinates
```bash
python manage.py seed_hospital_coordinates
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env` and configure:

```bash
# Redis (for Celery)
REDIS_URL=redis://localhost:6379/0

# Twilio SMS
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_NUMBER=+1234567890

# SendGrid Email
SENDGRID_API_KEY=your_sendgrid_api_key
EMAIL_FROM_ADDRESS=noreply@yourdomain.com
```

### 5. Start Redis Server
```bash
# On Ubuntu/Debian
sudo systemctl start redis-server

# On macOS with Homebrew
brew services start redis

# On Windows (if using WSL)
sudo service redis-server start
```

### 6. Start Celery Worker (Optional)
```bash
# In a separate terminal
celery -A bloodbankmanagement worker --loglevel=info
```

### 7. Start Django Server
```bash
python manage.py runserver
```

## 🎯 How to Use

### For Users:
1. **Find Hospitals**: Visit `/hospital-finder` or click "Find Hospitals" in navigation
2. **Get Location**: Click "Get My Location" to enable GPS
3. **View Results**: See nearby hospitals on map and in list view
4. **Request Notifications**: Click "Send SMS & Email Notifications" to receive contact info

### For Admins:
- **Manage Hospitals**: Add/edit hospital coordinates in Django admin
- **View Notifications**: Monitor notification jobs and their status
- **Update Stock**: Use admin interface to update blood stock levels

## 🔐 API Documentation

### 1. Find Nearby Hospitals
```bash
GET /api/nearby-hospitals/?lat=19.0760&lng=72.8777&radius_km=10
Authorization: Session-based (logged in user)

Response:
{
  "hospitals": [
    {
      "id": 1,
      "name": "Apollo Hospital",
      "address": "123 Medical Street",
      "city": "Mumbai",
      "state": "Maharashtra",
      "contact_phone": "+91-22-12345678",
      "contact_email": "info@apollo.com",
      "emergency_contact": "+91-22-87654321",
      "latitude": "19.0760",
      "longitude": "72.8777",
      "distance": "2.34",
      "blood_stock": {
        "A+": {"units": 50, "available": true},
        "O-": {"units": 0, "available": false}
      }
    }
  ],
  "total_found": 1,
  "search_radius_km": 10,
  "user_coordinates": {
    "latitude": 19.0760,
    "longitude": 72.8777
  }
}
```

### 2. Request Notifications
```bash
POST /api/notify-hospitals/
Content-Type: application/json
Authorization: Session-based

{
  "user_latitude": "19.0760",
  "user_longitude": "72.8777",
  "radius_km": 10,
  "notification_type": "BOTH"
}

Response:
{
  "job_id": 123,
  "status": "queued",
  "message": "Notification request queued successfully",
  "estimated_delivery": "2-5 minutes"
}
```

### 3. Check Notification Status
```bash
GET /api/notification-status/123/
Authorization: Session-based

Response:
{
  "id": 123,
  "user": "testuser",
  "status": "COMPLETED",
  "notification_type": "BOTH",
  "retry_count": 0,
  "created_at": "2025-01-XX...",
  "completed_at": "2025-01-XX..."
}
```

## 🧪 Testing

### Run Unit Tests
```bash
# Test location API
python manage.py test blood.tests.test_location_api

# Test notification tasks
python manage.py test blood.tests.test_notification_tasks

# Run all tests
python manage.py test blood.tests
```

### Manual Testing Steps

1. **Test Geolocation**:
   - Visit `/hospital-finder`
   - Click "Get My Location"
   - Verify location is acquired and map centers on your position

2. **Test Hospital Search**:
   - After getting location, verify hospitals appear on map and list
   - Try different radius values
   - Check that distance calculations are reasonable

3. **Test Notifications**:
   - Click "Send SMS & Email Notifications"
   - Check that notification job is created in admin
   - Verify email is received (if configured)

4. **Test Admin Interface**:
   - Go to Django admin
   - Edit hospital coordinates
   - View notification job logs

## 🔧 Configuration Options

### Rate Limiting
- Default: 5 notifications per hour per user
- Configurable in `settings.py`: `NOTIFICATION_RATE_LIMIT_PER_HOUR`

### Search Radius
- Minimum: 1 km
- Maximum: 100 km
- Default: 10 km

### Notification Retries
- Maximum retries: 3
- Exponential backoff: 2^retry_count minutes

## 🚨 Troubleshooting

### Common Issues:

1. **Geolocation Not Working**:
   - Ensure HTTPS is enabled (required for geolocation)
   - Check browser permissions
   - Verify JavaScript is enabled

2. **No Hospitals Found**:
   - Run `python manage.py seed_hospital_coordinates`
   - Check that hospitals have valid coordinates in admin
   - Increase search radius

3. **Notifications Not Sending**:
   - Verify environment variables are set
   - Check Celery worker is running
   - Review notification job logs in admin

4. **API Errors**:
   - Check user is authenticated
   - Verify coordinate format (decimal degrees)
   - Check rate limiting status

## 📱 Mobile Optimization

- Responsive design for all screen sizes
- Touch-friendly map controls
- Optimized for mobile geolocation
- Progressive enhancement for offline scenarios

## 🔄 Background Jobs

### Celery Tasks:
- `send_hospital_notifications` - Process notification requests
- `cleanup_old_notification_jobs` - Clean up old job records

### Monitoring:
- Use Django admin to monitor notification jobs
- Check Celery logs for task execution
- Monitor Redis for queue status

## 🛡️ Security Features

- Authentication required for all API endpoints
- Rate limiting to prevent abuse
- Input validation and sanitization
- CSRF protection for form submissions
- Coordinate range validation

## 📈 Performance Considerations

- API responses cached for 5 minutes
- Efficient distance calculations
- Database indexing on coordinates
- Pagination for large result sets

## 🔮 Future Enhancements

- Real-time hospital availability updates
- Push notifications for mobile apps
- Integration with hospital management systems
- Advanced filtering (blood type availability)
- Appointment booking integration

This feature provides a complete location-based hospital finder with notification capabilities, enhancing your Blood Bank Management System with modern geolocation services.