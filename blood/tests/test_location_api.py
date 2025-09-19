from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal
import json

from blood.models import Hospital, Stock, NotificationJob


class HospitalLocationAPITest(TestCase):
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        
        # Create test hospitals with coordinates
        self.hospital1 = Hospital.objects.create(
            name='Test Hospital 1',
            address='123 Test Street',
            city='Mumbai',
            state='Maharashtra',
            contact_phone='+91-22-12345678',
            contact_email='test1@hospital.com',
            emergency_contact='+91-22-87654321',
            latitude=Decimal('19.0760'),  # Mumbai coordinates
            longitude=Decimal('72.8777'),
            is_partner=True,
            blood_bank_available=True
        )
        
        self.hospital2 = Hospital.objects.create(
            name='Test Hospital 2',
            address='456 Test Avenue',
            city='Delhi',
            state='Delhi',
            contact_phone='+91-11-11223344',
            contact_email='test2@hospital.com',
            emergency_contact='+91-11-44332211',
            latitude=Decimal('28.7041'),  # Delhi coordinates
            longitude=Decimal('77.1025'),
            is_partner=True,
            blood_bank_available=True
        )
        
        # Create test blood stock
        Stock.objects.create(bloodgroup='A+', unit=50)
        Stock.objects.create(bloodgroup='O-', unit=25)
        Stock.objects.create(bloodgroup='B+', unit=0)
        
        # Login user
        self.client.login(username='testuser', password='testpass123')
    
    def test_nearby_hospitals_success(self):
        """Test successful nearby hospitals API call"""
        url = reverse('blood_api:nearby_hospitals')
        
        # Test with Mumbai coordinates (should find hospital1)
        response = self.client.get(url, {
            'lat': '19.0760',
            'lng': '72.8777',
            'radius_km': '10'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn('hospitals', data)
        self.assertIn('total_found', data)
        self.assertIn('search_radius_km', data)
        self.assertEqual(data['search_radius_km'], 10)
        
        # Should find at least one hospital
        self.assertGreaterEqual(data['total_found'], 1)
        
        # Check hospital data structure
        if data['hospitals']:
            hospital = data['hospitals'][0]
            self.assertIn('name', hospital)
            self.assertIn('distance', hospital)
            self.assertIn('blood_stock', hospital)
            self.assertIn('latitude', hospital)
            self.assertIn('longitude', hospital)
    
    def test_nearby_hospitals_missing_coordinates(self):
        """Test API with missing coordinates"""
        url = reverse('blood_api:nearby_hospitals')
        
        response = self.client.get(url, {'lat': '19.0760'})  # Missing longitude
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertEqual(data['code'], 'MISSING_COORDINATES')
    
    def test_nearby_hospitals_invalid_coordinates(self):
        """Test API with invalid coordinates"""
        url = reverse('blood_api:nearby_hospitals')
        
        # Invalid latitude (out of range)
        response = self.client.get(url, {
            'lat': '95.0000',  # Invalid latitude
            'lng': '72.8777'
        })
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['code'], 'INVALID_LATITUDE')
    
    def test_nearby_hospitals_unauthenticated(self):
        """Test API without authentication"""
        self.client.logout()
        url = reverse('blood_api:nearby_hospitals')
        
        response = self.client.get(url, {
            'lat': '19.0760',
            'lng': '72.8777'
        })
        
        self.assertEqual(response.status_code, 403)
    
    def test_distance_calculation(self):
        """Test Haversine distance calculation"""
        # Test distance between Mumbai and Delhi (approximately 1150 km)
        mumbai_lat, mumbai_lng = Decimal('19.0760'), Decimal('72.8777')
        
        distance = self.hospital2.calculate_distance(mumbai_lat, mumbai_lng)
        
        # Distance should be approximately 1150 km (±50 km tolerance)
        self.assertIsNotNone(distance)
        self.assertGreater(distance, 1100)
        self.assertLess(distance, 1200)
    
    def test_distance_calculation_no_coordinates(self):
        """Test distance calculation with missing hospital coordinates"""
        hospital_no_coords = Hospital.objects.create(
            name='No Coords Hospital',
            address='Test Address',
            city='Test City',
            state='Test State',
            contact_phone='+91-00-00000000',
            contact_email='test@test.com',
            emergency_contact='+91-00-11111111',
            # No latitude/longitude
            is_partner=True
        )
        
        distance = hospital_no_coords.calculate_distance(Decimal('19.0760'), Decimal('72.8777'))
        self.assertIsNone(distance)


class NotificationAPITest(TestCase):
    def setUp(self):
        """Set up test data for notification tests"""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
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
        
        # Login user
        self.client.login(username='testuser', password='testpass123')
    
    def test_notify_hospitals_success(self):
        """Test successful notification request"""
        url = reverse('blood_api:notify_hospitals')
        
        data = {
            'user_latitude': '19.0760',
            'user_longitude': '72.8777',
            'radius_km': 10,
            'notification_type': 'EMAIL'
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        response_data = response.json()
        
        self.assertIn('job_id', response_data)
        self.assertIn('status', response_data)
        
        # Check that notification job was created
        job = NotificationJob.objects.get(id=response_data['job_id'])
        self.assertEqual(job.user, self.user)
        self.assertEqual(job.notification_type, 'EMAIL')
    
    def test_notify_hospitals_invalid_data(self):
        """Test notification request with invalid data"""
        url = reverse('blood_api:notify_hospitals')
        
        data = {
            'user_latitude': '95.0000',  # Invalid latitude
            'user_longitude': '72.8777',
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertEqual(response_data['code'], 'VALIDATION_ERROR')
    
    def test_notification_status(self):
        """Test notification status endpoint"""
        # Create a notification job
        job = NotificationJob.objects.create(
            user=self.user,
            user_latitude=Decimal('19.0760'),
            user_longitude=Decimal('72.8777'),
            radius_km=10,
            notification_type='BOTH'
        )
        
        url = reverse('blood_api:notification_status', kwargs={'job_id': job.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data['id'], job.id)
        self.assertEqual(data['status'], 'PENDING')
        self.assertEqual(data['notification_type'], 'BOTH')
    
    def test_notification_status_not_found(self):
        """Test notification status for non-existent job"""
        url = reverse('blood_api:notification_status', kwargs={'job_id': 99999})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data['code'], 'JOB_NOT_FOUND')
    
    def test_blood_stock_summary(self):
        """Test blood stock summary endpoint"""
        url = reverse('blood_api:blood_stock_summary')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn('blood_stock', data)
        self.assertIn('total_units', data)
        self.assertIn('last_updated', data)
        
        # Check blood stock data
        blood_stock = data['blood_stock']
        self.assertIn('A+', blood_stock)
        self.assertEqual(blood_stock['A+']['units'], 50)
        self.assertTrue(blood_stock['A+']['available'])
        
        self.assertIn('B+', blood_stock)
        self.assertEqual(blood_stock['B+']['units'], 0)
        self.assertFalse(blood_stock['B+']['available'])


class NotificationJobModelTest(TestCase):
    def setUp(self):
        """Set up test data for model tests"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
    
    def test_notification_job_creation(self):
        """Test NotificationJob model creation"""
        job = NotificationJob.objects.create(
            user=self.user,
            user_latitude=Decimal('19.0760'),
            user_longitude=Decimal('72.8777'),
            radius_km=15,
            notification_type='SMS'
        )
        
        self.assertEqual(job.user, self.user)
        self.assertEqual(job.status, 'PENDING')
        self.assertEqual(job.retry_count, 0)
        self.assertEqual(job.max_retries, 3)
        self.assertTrue(job.can_retry)  # Should be able to retry initially
    
    def test_notification_job_mark_completed(self):
        """Test marking notification job as completed"""
        job = NotificationJob.objects.create(
            user=self.user,
            user_latitude=Decimal('19.0760'),
            user_longitude=Decimal('72.8777')
        )
        
        job.mark_completed()
        
        self.assertEqual(job.status, 'COMPLETED')
        self.assertIsNotNone(job.completed_at)
    
    def test_notification_job_mark_failed(self):
        """Test marking notification job as failed"""
        job = NotificationJob.objects.create(
            user=self.user,
            user_latitude=Decimal('19.0760'),
            user_longitude=Decimal('72.8777')
        )
        
        error_message = "Test error message"
        job.mark_failed(error_message)
        
        self.assertEqual(job.status, 'FAILED')
        self.assertEqual(job.error_message, error_message)
    
    def test_notification_job_retry_logic(self):
        """Test notification job retry logic"""
        job = NotificationJob.objects.create(
            user=self.user,
            user_latitude=Decimal('19.0760'),
            user_longitude=Decimal('72.8777'),
            max_retries=2
        )
        
        # Initially can retry
        self.assertTrue(job.can_retry)
        
        # After marking as failed, should be able to retry
        job.mark_failed("First failure")
        self.assertTrue(job.can_retry)
        
        # Increment retry count
        job.increment_retry()
        self.assertEqual(job.retry_count, 1)
        self.assertTrue(job.can_retry)
        
        # After max retries, should not be able to retry
        job.increment_retry()
        self.assertEqual(job.retry_count, 2)
        self.assertFalse(job.can_retry)


class HospitalModelTest(TestCase):
    def setUp(self):
        """Set up test data for hospital model tests"""
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
    
    def test_hospital_has_coordinates(self):
        """Test hospital coordinates property"""
        self.assertTrue(self.hospital.has_coordinates)
        
        # Test hospital without coordinates
        hospital_no_coords = Hospital.objects.create(
            name='No Coords Hospital',
            address='Test Address',
            city='Test City',
            state='Test State',
            contact_phone='+91-00-00000000',
            contact_email='test@test.com',
            emergency_contact='+91-00-11111111',
            is_partner=True
        )
        
        self.assertFalse(hospital_no_coords.has_coordinates)
    
    def test_distance_calculation_accuracy(self):
        """Test distance calculation accuracy with known coordinates"""
        # Test distance from Mumbai to Delhi (known distance ~1150 km)
        delhi_lat, delhi_lng = Decimal('28.7041'), Decimal('77.1025')
        
        distance = self.hospital.calculate_distance(delhi_lat, delhi_lng)
        
        # Should be approximately 1150 km (±100 km tolerance for test)
        self.assertIsNotNone(distance)
        self.assertGreater(distance, 1050)
        self.assertLess(distance, 1250)
    
    def test_distance_calculation_same_location(self):
        """Test distance calculation for same location"""
        distance = self.hospital.calculate_distance(
            self.hospital.latitude, 
            self.hospital.longitude
        )
        
        # Distance should be very close to 0
        self.assertIsNotNone(distance)
        self.assertLess(distance, 0.1)  # Less than 100 meters