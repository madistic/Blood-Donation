from django.db import models
from patient import models as pmodels
from donor import models as dmodels
from django.contrib.auth.models import User
from datetime import date

class Stock(models.Model):
    bloodgroup=models.CharField(max_length=10)
    unit=models.PositiveIntegerField(default=0)
    def __str__(self):
        return self.bloodgroup

class BloodRequest(models.Model):
    request_by_patient=models.ForeignKey(pmodels.Patient,null=True,on_delete=models.CASCADE)
    request_by_donor=models.ForeignKey(dmodels.Donor,null=True,on_delete=models.CASCADE)
    patient_name=models.CharField(max_length=30)
    patient_age=models.PositiveIntegerField()
    reason=models.CharField(max_length=500)
    bloodgroup=models.CharField(max_length=10)
    unit=models.PositiveIntegerField(default=0)
    status=models.CharField(max_length=20,default="Pending")
    date=models.DateField(auto_now=True)
    def __str__(self):
        return self.bloodgroup

# Gamification System - Certificates for Donors
class Certificate(models.Model):
    CERTIFICATE_TYPES = [
        ('FIRST_DONATION', 'First Time Donor'),
        ('REGULAR_DONOR', 'Regular Donor (5+ donations)'),
        ('HERO_DONOR', 'Hero Donor (10+ donations)'),
        ('LIFE_SAVER', 'Life Saver (20+ donations)'),
        ('BLOOD_CHAMPION', 'Blood Champion (50+ donations)'),
    ]
    
    donor = models.ForeignKey(dmodels.Donor, on_delete=models.CASCADE)
    certificate_type = models.CharField(max_length=20, choices=CERTIFICATE_TYPES)
    issued_date = models.DateField(auto_now_add=True)
    donation_count = models.PositiveIntegerField()
    certificate_id = models.CharField(max_length=20, unique=True)
    
    def __str__(self):
        return f"{self.donor.get_name} - {self.get_certificate_type_display()}"
    
    def save(self, *args, **kwargs):
        if not self.certificate_id:
            self.certificate_id = f"CERT{self.donor.id}{date.today().strftime('%Y%m%d')}"
        super().save(*args, **kwargs)

# Sponsors and Hospitals System
class Sponsor(models.Model):
    name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='sponsors/', null=True, blank=True)
    description = models.TextField()
    website = models.URLField(blank=True)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    address = models.TextField()
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class Hospital(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField()
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    contact_phone = models.CharField(max_length=20)
    contact_email = models.EmailField()
    emergency_contact = models.CharField(max_length=20)
    blood_bank_available = models.BooleanField(default=True)
    is_partner = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name

# Blood Camp Management System
class BloodCamp(models.Model):
    CAMP_STATUS = [
        ('PLANNED', 'Planned'),
        ('ONGOING', 'Ongoing'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    organizer = models.CharField(max_length=100)
    sponsor = models.ForeignKey(Sponsor, on_delete=models.SET_NULL, null=True, blank=True)
    hospital_partner = models.ForeignKey(Hospital, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Location details
    venue = models.CharField(max_length=200)
    address = models.TextField()
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    
    # Date and time
    start_date = models.DateField()
    end_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    # Camp details
    target_donors = models.PositiveIntegerField(default=50)
    registered_donors = models.PositiveIntegerField(default=0)
    actual_donors = models.PositiveIntegerField(default=0)
    blood_collected = models.PositiveIntegerField(default=0)  # in units
    
    status = models.CharField(max_length=20, choices=CAMP_STATUS, default='PLANNED')
    created_date = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.start_date}"
    
    @property
    def is_upcoming(self):
        return self.start_date > date.today()
    
    @property
    def is_ongoing(self):
        return self.start_date <= date.today() <= self.end_date

class CampRegistration(models.Model):
    camp = models.ForeignKey(BloodCamp, on_delete=models.CASCADE)
    donor = models.ForeignKey(dmodels.Donor, on_delete=models.CASCADE)
    registered_date = models.DateTimeField(auto_now_add=True)
    attended = models.BooleanField(default=False)
    donated = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['camp', 'donor']
    
    def __str__(self):
        return f"{self.donor.get_name} - {self.camp.name}"