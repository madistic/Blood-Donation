import os
import logging
from decimal import Decimal
from django.utils import timezone
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import send_mail

# Optional imports for external services
try:
    from celery import shared_task
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    # Mock decorator for when Celery is not available
    def shared_task(func):
        return func

try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

try:
    import sendgrid
    from sendgrid.helpers.mail import Mail
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False

from .models import NotificationJob, Hospital, Stock

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_hospital_notifications(self, job_id):
    """
    Celery task to send hospital notifications via SMS and Email
    
    Args:
        job_id: NotificationJob ID to process
    
    Returns:
        dict: Task result with status and details
    """
    try:
        # Get notification job
        job = NotificationJob.objects.get(id=job_id)
        job.status = 'PROCESSING'
        job.save()
        
        # Find nearby hospitals
        hospitals = Hospital.objects.filter(
            is_partner=True,
            latitude__isnull=False,
            longitude__isnull=False
        )
        
        nearby_hospitals = []
        for hospital in hospitals:
            distance = hospital.calculate_distance(job.user_latitude, job.user_longitude)
            if distance is not None and distance <= job.radius_km:
                hospital.distance = round(distance, 2)
                nearby_hospitals.append(hospital)
        
        nearby_hospitals.sort(key=lambda h: h.distance)
        
        if not nearby_hospitals:
            job.mark_failed("No hospitals found within specified radius")
            return {'status': 'failed', 'reason': 'no_hospitals_found'}
        
        # Get blood stock information
        blood_stock = {}
        stocks = Stock.objects.all()
        for stock in stocks:
            blood_stock[stock.bloodgroup] = stock.unit
        
        # Prepare notification content
        context = {
            'user': job.user,
            'hospitals': nearby_hospitals[:5],  # Limit to top 5 closest
            'blood_stock': blood_stock,
            'search_radius': job.radius_km,
            'total_hospitals': len(nearby_hospitals)
        }
        
        # Send notifications based on type
        results = {'sms': None, 'email': None}
        
        if job.notification_type in ['SMS', 'BOTH']:
            results['sms'] = send_sms_notification(job.user, context)
        
        if job.notification_type in ['EMAIL', 'BOTH']:
            results['email'] = send_email_notification(job.user, context)
        
        # Check if any notification succeeded
        success = any(results.values())
        
        if success:
            job.mark_completed()
            return {
                'status': 'completed',
                'results': results,
                'hospitals_found': len(nearby_hospitals)
            }
        else:
            error_msg = f"All notifications failed. SMS: {results['sms']}, Email: {results['email']}"
            job.mark_failed(error_msg)
            return {'status': 'failed', 'reason': 'all_notifications_failed'}
            
    except NotificationJob.DoesNotExist:
        logger.error(f"NotificationJob {job_id} not found")
        return {'status': 'failed', 'reason': 'job_not_found'}
        
    except Exception as e:
        logger.error(f"Error in send_hospital_notifications task: {str(e)}")
        
        try:
            job = NotificationJob.objects.get(id=job_id)
            job.increment_retry()
            
            if job.can_retry:
                # Exponential backoff: 2^retry_count minutes
                countdown = 60 * (2 ** job.retry_count)
                raise self.retry(countdown=countdown, exc=e)
            else:
                job.mark_failed(str(e))
        except NotificationJob.DoesNotExist:
            pass
        
        return {'status': 'failed', 'reason': str(e)}


def send_sms_notification(user, context):
    """
    Send SMS notification using Twilio
    
    Args:
        user: User object
        context: Template context with hospital data
    
    Returns:
        str: Success message or error description
    """
    if not TWILIO_AVAILABLE:
        return "Twilio not available"
    
    try:
        # Get Twilio credentials from environment
        account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        from_number = os.environ.get('TWILIO_FROM_NUMBER')
        
        if not all([account_sid, auth_token, from_number]):
            logger.error("Twilio credentials not configured")
            return "SMS service not configured"
        
        # Get user phone number (assuming it's stored in profile)
        user_phone = getattr(user, 'phone', None)
        if not user_phone:
            # Try to get from donor or patient profile
            try:
                from donor.models import Donor
                donor = Donor.objects.get(user=user)
                user_phone = donor.mobile
            except:
                try:
                    from patient.models import Patient
                    patient = Patient.objects.get(user=user)
                    user_phone = patient.mobile
                except:
                    return "User phone number not found"
        
        if not user_phone:
            return "Phone number not available"
        
        # Format phone number (add country code if needed)
        if not user_phone.startswith('+'):
            user_phone = '+91' + user_phone.lstrip('0')  # Assuming India
        
        # Create SMS content
        hospitals_text = "\n".join([
            f"{h.name} ({h.distance}km) - {h.contact_phone}"
            for h in context['hospitals'][:3]
        ])
        
        message_body = f"""🏥 Nearby Hospitals ({context['search_radius']}km radius):

{hospitals_text}

Blood Stock Available:
{', '.join([f"{bg}:{units}" for bg, units in context['blood_stock'].items() if units > 0])}

Emergency: Call hospitals directly
- Blood Bank Management System"""
        
        # Send SMS via Twilio
        client = TwilioClient(account_sid, auth_token)
        message = client.messages.create(
            body=message_body,
            from_=from_number,
            to=user_phone
        )
        
        logger.info(f"SMS sent successfully to {user_phone}, SID: {message.sid}")
        return f"SMS sent successfully (SID: {message.sid})"
        
    except Exception as e:
        logger.error(f"Error sending SMS: {str(e)}")
        return f"SMS failed: {str(e)}"


def send_email_notification(user, context):
    """
    Send email notification using SendGrid or Django email
    
    Args:
        user: User object
        context: Template context with hospital data
    
    Returns:
        str: Success message or error description
    """
    try:
        # Prepare email content
        subject = f"🏥 Nearby Hospitals & Blood Stock - {context['total_hospitals']} found"
        
        # Create HTML email content
        html_content = render_to_string('blood/email/hospital_notification.html', context)
        
        # Create plain text version
        text_content = f"""
Nearby Hospitals ({context['search_radius']}km radius):

"""
        for hospital in context['hospitals']:
            text_content += f"""
{hospital.name} ({hospital.distance}km away)
📍 {hospital.address}, {hospital.city}
📞 {hospital.contact_phone}
📧 {hospital.contact_email}
🚨 Emergency: {hospital.emergency_contact}

"""
        
        text_content += f"""
Current Blood Stock:
"""
        for blood_group, units in context['blood_stock'].items():
            status_text = "Available" if units > 10 else "Low Stock" if units > 0 else "Unavailable"
            text_content += f"{blood_group}: {units} units ({status_text})\n"
        
        text_content += """
For emergencies, contact hospitals directly.

Best regards,
Blood Bank Management System
"""
        
        # Try SendGrid first, fallback to Django email
        if SENDGRID_AVAILABLE and os.environ.get('SENDGRID_API_KEY'):
            return send_email_via_sendgrid(user.email, subject, html_content, text_content)
        else:
            return send_email_via_django(user.email, subject, html_content, text_content)
            
    except Exception as e:
        logger.error(f"Error preparing email: {str(e)}")
        return f"Email preparation failed: {str(e)}"


def send_email_via_sendgrid(to_email, subject, html_content, text_content):
    """Send email using SendGrid API"""
    try:
        api_key = os.environ.get('SENDGRID_API_KEY')
        from_email = os.environ.get('EMAIL_FROM_ADDRESS', 'noreply@bloodbank.com')
        
        sg = sendgrid.SendGridAPIClient(api_key=api_key)
        
        mail = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            html_content=html_content,
            plain_text_content=text_content
        )
        
        response = sg.send(mail)
        logger.info(f"SendGrid email sent to {to_email}, status: {response.status_code}")
        return f"Email sent via SendGrid (Status: {response.status_code})"
        
    except Exception as e:
        logger.error(f"SendGrid email failed: {str(e)}")
        return f"SendGrid failed: {str(e)}"


def send_email_via_django(to_email, subject, html_content, text_content):
    """Send email using Django's email backend"""
    try:
        from django.core.mail import EmailMultiAlternatives
        
        from_email = os.environ.get('EMAIL_FROM_ADDRESS', settings.DEFAULT_FROM_EMAIL)
        
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[to_email]
        )
        msg.attach_alternative(html_content, "text/html")
        
        result = msg.send()
        
        if result:
            logger.info(f"Django email sent to {to_email}")
            return "Email sent via Django"
        else:
            return "Django email failed"
            
    except Exception as e:
        logger.error(f"Django email failed: {str(e)}")
        return f"Django email failed: {str(e)}"


def process_notification_sync(job_id):
    """
    Synchronous version of notification processing for when Celery is not available
    
    Args:
        job_id: NotificationJob ID to process
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # This is a simplified synchronous version
        job = NotificationJob.objects.get(id=job_id)
        job.status = 'PROCESSING'
        job.save()
        
        # Find nearby hospitals
        hospitals = Hospital.objects.filter(
            is_partner=True,
            latitude__isnull=False,
            longitude__isnull=False
        )
        
        nearby_hospitals = []
        for hospital in hospitals:
            distance = hospital.calculate_distance(job.user_latitude, job.user_longitude)
            if distance is not None and distance <= job.radius_km:
                hospital.distance = round(distance, 2)
                nearby_hospitals.append(hospital)
        
        if not nearby_hospitals:
            job.mark_failed("No hospitals found within specified radius")
            return False
        
        # Get blood stock
        blood_stock = {}
        stocks = Stock.objects.all()
        for stock in stocks:
            blood_stock[stock.bloodgroup] = stock.unit
        
        context = {
            'user': job.user,
            'hospitals': nearby_hospitals[:5],
            'blood_stock': blood_stock,
            'search_radius': job.radius_km,
            'total_hospitals': len(nearby_hospitals)
        }
        
        # Send email notification (simplified)
        email_result = send_email_notification(job.user, context)
        
        if "sent" in email_result.lower():
            job.mark_completed()
            return True
        else:
            job.mark_failed(email_result)
            return False
            
    except Exception as e:
        logger.error(f"Error in process_notification_sync: {str(e)}")
        try:
            job = NotificationJob.objects.get(id=job_id)
            job.mark_failed(str(e))
        except:
            pass
        return False