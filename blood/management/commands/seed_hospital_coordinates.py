from django.core.management.base import BaseCommand
from blood.models import Hospital

class Command(BaseCommand):
    help = 'Seed hospital coordinates for existing hospitals'

    def handle(self, *args, **options):
        # Real coordinates for major Indian hospitals
        hospital_coordinates = {
            'Apollo Hospital': {'latitude': 13.0827, 'longitude': 80.2707},
            'Fortis Hospital': {'latitude': 28.4595, 'longitude': 77.0266},
            'AIIMS': {'latitude': 28.5672, 'longitude': 77.2100},
            'KEM Hospital': {'latitude': 19.0176, 'longitude': 72.8562},
            'SGPGI': {'latitude': 26.8467, 'longitude': 80.9462},
            'Manipal Hospital': {'latitude': 13.3525, 'longitude': 74.7949},
            'Christian Medical College': {'latitude': 12.9249, 'longitude': 79.1353},
            'Ruby Hall Clinic': {'latitude': 18.5204, 'longitude': 73.8567},
        }
        
        updated_count = 0
        
        for hospital_name, coords in hospital_coordinates.items():
            try:
                hospital = Hospital.objects.get(name__icontains=hospital_name.split()[0])
                hospital.latitude = coords['latitude']
                hospital.longitude = coords['longitude']
                hospital.save()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Updated coordinates for {hospital.name}: '
                        f'{coords["latitude"]}, {coords["longitude"]}'
                    )
                )
                updated_count += 1
                
            except Hospital.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'Hospital not found: {hospital_name}')
                )
            except Hospital.MultipleObjectsReturned:
                # Update the first match
                hospital = Hospital.objects.filter(name__icontains=hospital_name.split()[0]).first()
                if hospital:
                    hospital.latitude = coords['latitude']
                    hospital.longitude = coords['longitude']
                    hospital.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Updated coordinates for {hospital.name}: '
                            f'{coords["latitude"]}, {coords["longitude"]}'
                        )
                    )
                    updated_count += 1
        
        # Add some additional sample hospitals with coordinates
        sample_hospitals = [
            {
                'name': 'City General Hospital',
                'address': '123 Medical District, Central Area',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'contact_phone': '+91-22-12345678',
                'contact_email': 'info@citygeneral.com',
                'emergency_contact': '+91-22-87654321',
                'latitude': 19.0760,
                'longitude': 72.8777,
                'is_partner': True,
                'blood_bank_available': True
            },
            {
                'name': 'Metro Medical Center',
                'address': '456 Healthcare Avenue, Tech City',
                'city': 'Bangalore',
                'state': 'Karnataka',
                'contact_phone': '+91-80-11223344',
                'contact_email': 'contact@metromedical.com',
                'emergency_contact': '+91-80-44332211',
                'latitude': 12.9716,
                'longitude': 77.5946,
                'is_partner': True,
                'blood_bank_available': True
            },
            {
                'name': 'Regional Blood Center',
                'address': '789 Health Complex, Medical Zone',
                'city': 'Delhi',
                'state': 'Delhi',
                'contact_phone': '+91-11-55667788',
                'contact_email': 'blood@regionalcenter.com',
                'emergency_contact': '+91-11-88776655',
                'latitude': 28.7041,
                'longitude': 77.1025,
                'is_partner': True,
                'blood_bank_available': True
            }
        ]
        
        for hospital_data in sample_hospitals:
            hospital, created = Hospital.objects.get_or_create(
                name=hospital_data['name'],
                defaults=hospital_data
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created new hospital: {hospital.name}')
                )
                updated_count += 1
            else:
                # Update coordinates if missing
                if not hospital.has_coordinates:
                    hospital.latitude = hospital_data['latitude']
                    hospital.longitude = hospital_data['longitude']
                    hospital.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'Added coordinates to existing hospital: {hospital.name}')
                    )
                    updated_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nCompleted! Updated/created {updated_count} hospitals with coordinates.'
            )
        )
        
        # Show summary
        total_hospitals = Hospital.objects.count()
        hospitals_with_coords = Hospital.objects.filter(
            latitude__isnull=False, 
            longitude__isnull=False
        ).count()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Summary: {hospitals_with_coords}/{total_hospitals} hospitals now have coordinates'
            )
        )