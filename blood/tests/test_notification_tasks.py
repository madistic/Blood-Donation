from django.test import TestCase
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock
from decimal import Decimal

from blood.models import Hospital, Stock, NotificationJob
from blood.tasks import send_hospital_notifications, send_sms_notification, send_email_notification


class NotificationTaskTest(TestCase):
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
        
        # Create test hospital
        self.hospital = Hospital.objects.create(
            name='Test Hospital',
            address='123 Test Street',
            city='Mumbai',
            state='Maharashtra',
            contact_phone='+91-22-12345678',
            contact_email='test@hospital.com',
            emergency_contact='+91-22-87654321',
            latitude=Decimal('19.0760'),
            longitude=Decimal('72.8777'),
            is_partner=True,
            blood_bank_available=True
        )
        
        # Create blood stock
        Stock.objects.create(bloodgroup='A+', unit=50)
        Stock.objects.create(bloodgroup='O-', unit=25)
        
        # Create notification job
        self.job = NotificationJob.objects.create(
            user=self.user,
            user_latitude=Decimal('19.0760'),
            user_longitude=Decimal('72.8777'),
            radius_km=10,
            notification_type='BOTH'
        )
    
    def test_notification_job_processing(self):
        """Test notification job processing logic"""
        # Test that job finds nearby hospitals
        result = send_hospital_notifications(self.job.id)
        
        # Refresh job from database
        self.job.refresh_from_db()
        
        # Job should have been processed
        self.assertIn(self.job.status, ['COMPLETED', 'FAILED'])
        
        if self.job.status == 'COMPLETED':
            self.assertIsNotNone(self.job.completed_at)
        elif self.job.status == 'FAILED':
            self.assertIsNotNone(self.job.error_message)
    
    def test_notification_job_no_hospitals(self):
        """Test notification job when no hospitals are found"""
        # Create job with coordinates far from any hospital
        job = NotificationJob.objects.create(
            user=self.user,
            user_latitude=Decimal('0.0000'),  # Middle of ocean
            user_longitude=Decimal('0.0000'),
            radius_km=1,  # Very small radius
            notification_type='EMAIL'
        )
        
        result = send_hospital_notifications(job.id)
        
        # Refresh job from database
        job.refresh_from_db()
        
        self.assertEqual(job.status, 'FAILED')
        self.assertIn('No hospitals found', job.error_message)
    
    @patch('blood.tasks.TwilioClient')
    @patch('blood.tasks.TWILIO_AVAILABLE', True)
    @patch.dict('os.environ', {
        'TWILIO_ACCOUNT_SID': 'test_sid',
        'TWILIO_AUTH_TOKEN': 'test_token',
        'TWILIO_FROM_NUMBER': '+1234567890'
    })
    def test_sms_notification_success(self, mock_twilio_client):
        """Test successful SMS notification"""
        # Mock Twilio client
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.sid = 'test_message_sid'
        mock_client.messages.create.return_value = mock_message
        mock_twilio_client.return_value = mock_client
        
        # Mock user phone number
        with patch('donor.models.Donor.objects.get') as mock_donor:
            mock_donor.return_value.mobile = '+919876543210'
            
            context = {
                'user': self.user,
                'hospitals': [self.hospital],
                'blood_stock': {'A+': 50, 'O-': 25},
                'search_radius': 10,
                'total_hospitals': 1
            }
            
            result = send_sms_notification(self.user, context)
            
            self.assertIn('SMS sent successfully', result)
            mock_client.messages.create.assert_called_once()
    
    @patch('blood.tasks.TWILIO_AVAILABLE', False)
    def test_sms_notification_unavailable(self):
        """Test SMS notification when Twilio is not available"""
        context = {
            'user': self.user,
            'hospitals': [self.hospital],
            'blood_stock': {'A+': 50},
            'search_radius': 10,
            'total_hospitals': 1
        }
        
        result = send_sms_notification(self.user, context)
        self.assertEqual(result, "Twilio not available")
    
    @patch('blood.tasks.send_mail')
    def test_email_notification_django(self, mock_send_mail):
        """Test email notification using Django backend"""
        mock_send_mail.return_value = True
        
        context = {
            'user': self.user,
            'hospitals': [self.hospital],
            'blood_stock': {'A+': 50, 'O-': 25},
            'search_radius': 10,
            'total_hospitals': 1
        }
        
        result = send_email_notification(self.user, context)
        
        self.assertIn('Email sent', result)
    
    def test_notification_job_retry_logic(self):
        """Test notification job retry mechanism"""
        job = NotificationJob.objects.create(
            user=self.user,
            user_latitude=Decimal('19.0760'),
            user_longitude=Decimal('72.8777'),
            max_retries=2
        )
        
        # Initially can retry
        self.assertTrue(job.can_retry)
        
        # Mark as failed and increment retry
        job.mark_failed("Test failure")
        job.increment_retry()
        
        self.assertEqual(job.retry_count, 1)
        self.assertTrue(job.can_retry)
        
        # After max retries
        job.increment_retry()
        self.assertEqual(job.retry_count, 2)
        self.assertFalse(job.can_retry)