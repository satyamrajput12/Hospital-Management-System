import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from departments.models import Department
from doctors.models import Doctor, DoctorAvailability

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed the database with sample departments, doctors and an admin user.'

    def handle(self, *args, **options):
        # Admin
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin', email='admin@cityhospital.com', password='Admin@12345',
                first_name='Hospital', last_name='Admin', role=User.Role.ADMIN
            )
            self.stdout.write(self.style.SUCCESS('Created admin user (admin / Admin@12345)'))

        dept_data = [
            ('Cardiology', 'Heart and cardiovascular care', '❤️'),
            ('Neurology', 'Brain and nervous system care', '🧠'),
            ('Orthopedics', 'Bones, joints and muscles', '🦴'),
            ('Pediatrics', 'Child healthcare', '🧒'),
            ('Dermatology', 'Skin, hair and nail care', '🧴'),
            ('General Medicine', 'General checkups and treatment', '🩺'),
        ]
        departments = {}
        for name, desc, icon in dept_data:
            dept, _ = Department.objects.get_or_create(name=name, defaults={'description': desc, 'icon': icon})
            departments[name] = dept
        self.stdout.write(self.style.SUCCESS(f'Ensured {len(departments)} departments.'))

        doctor_data = [
            ('drsharma', 'Anil', 'Sharma', 'Cardiology', 'Interventional Cardiologist', 'MD, DM Cardiology', 12, 800),
            ('drgupta', 'Priya', 'Gupta', 'Neurology', 'Neurologist', 'MD, DM Neurology', 9, 900),
            ('drpatel', 'Rohan', 'Patel', 'Orthopedics', 'Orthopedic Surgeon', 'MS Ortho', 15, 700),
            ('drmehta', 'Sneha', 'Mehta', 'Pediatrics', 'Pediatrician', 'MD Pediatrics', 7, 500),
            ('drkhan', 'Imran', 'Khan', 'Dermatology', 'Dermatologist', 'MD Dermatology', 6, 600),
            ('drrao', 'Lakshmi', 'Rao', 'General Medicine', 'General Physician', 'MBBS, MD', 10, 400),
        ]
        for username, first, last, dept_name, spec, qual, exp, fee in doctor_data:
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username, email=f'{username}@cityhospital.com', password='Doctor@12345',
                    first_name=first, last_name=last, role=User.Role.DOCTOR
                )
                doctor = Doctor.objects.create(
                    user=user, department=departments[dept_name], specialization=spec,
                    qualification=qual, experience_years=exp, consultation_fee=fee,
                    bio=f'{first} {last} is a dedicated {spec.lower()} with {exp} years of experience.'
                )
                for day in ['MON', 'WED', 'FRI']:
                    DoctorAvailability.objects.create(
                        doctor=doctor, day_of_week=day,
                        start_time=datetime.time(9, 0), end_time=datetime.time(13, 0),
                        slot_duration_minutes=30
                    )
                self.stdout.write(self.style.SUCCESS(f'Created doctor {username} / Doctor@12345'))

        self.stdout.write(self.style.SUCCESS('Seeding complete.'))
