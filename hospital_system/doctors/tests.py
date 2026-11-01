import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from departments.models import Department
from doctors.models import Doctor, DoctorAvailability

User = get_user_model()


class DoctorAndAvailabilityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.department = Department.objects.create(name='Cardiology')
        self.neurology = Department.objects.create(name='Neurology')

        self.doc_user = User.objects.create_user(
            username='doctor_sarah',
            email='sarah@hospital.com',
            password='Password123!',
            first_name='Sarah',
            last_name='Connor',
            role=User.Role.DOCTOR,
            is_email_verified=True,
            is_active=True
        )
        self.doctor = Doctor.objects.create(
            user=self.doc_user,
            department=self.department,
            specialization='Cardiologist',
            qualification='MBBS, MD',
            experience_years=10,
            consultation_fee=150.00,
            is_active=True
        )

        self.patient = User.objects.create_user(
            username='patient_mark',
            email='mark@hospital.com',
            password='Password123!',
            role=User.Role.PATIENT,
            is_email_verified=True,
            is_active=True
        )

        self.admin = User.objects.create_user(
            username='hospital_admin',
            email='admin@hospital.com',
            password='Password123!',
            role=User.Role.ADMIN,
            is_staff=True,
            is_email_verified=True,
            is_active=True
        )

    def test_availability_time_validation(self):
        # start_time >= end_time should fail validation
        slot = DoctorAvailability(
            doctor=self.doctor,
            day_of_week='MON',
            start_time=datetime.time(12, 0),
            end_time=datetime.time(10, 0),
            slot_duration_minutes=30
        )
        with self.assertRaises(ValidationError):
            slot.full_clean()

    def test_availability_overlapping_slot_prevented(self):
        # Create initial slot: 09:00 - 12:00 on MON
        DoctorAvailability.objects.create(
            doctor=self.doctor,
            day_of_week='MON',
            start_time=datetime.time(9, 0),
            end_time=datetime.time(12, 0),
            slot_duration_minutes=30
        )

        # Overlapping slot: 10:00 - 13:00 on MON
        overlapping_slot = DoctorAvailability(
            doctor=self.doctor,
            day_of_week='MON',
            start_time=datetime.time(10, 0),
            end_time=datetime.time(13, 0),
            slot_duration_minutes=30
        )
        with self.assertRaises(ValidationError):
            overlapping_slot.full_clean()

    def test_doctor_self_profile_edit(self):
        self.client.login(username='doctor_sarah', password='Password123!')
        url = reverse('doctors:doctor_profile_edit')
        
        # Valid edit
        resp = self.client.post(url, {
            'specialization': 'Interventional Cardiologist',
            'qualification': 'MBBS, MD, FACC',
            'experience_years': 12,
            'consultation_fee': 200.00,
            'bio': 'Experienced cardiology specialist.',
            'phone': '9876543210',
            'first_name': 'Sarah',
            'last_name': 'Connor-Smith',
            'is_available': True,
        })
        self.assertRedirects(resp, reverse('doctors:profile_edit'))
        self.doctor.refresh_from_db()
        self.assertEqual(self.doctor.specialization, 'Interventional Cardiologist')
        self.assertEqual(float(self.doctor.consultation_fee), 200.00)

    def test_patient_cannot_edit_doctor_profile(self):
        self.client.login(username='patient_mark', password='Password123!')
        url = reverse('doctors:doctor_profile_edit')
        resp = self.client.get(url)
        self.assertRedirects(resp, reverse('corepages:redirect_dashboard'), target_status_code=302)

    def test_doctor_search_and_filtering(self):
        url = reverse('doctors:doctor_list')
        
        # Search by name match
        resp = self.client.get(url, {'q': 'Sarah'})
        self.assertContains(resp, 'Sarah')

        # Filter by department match
        resp2 = self.client.get(url, {'department': self.department.id})
        self.assertContains(resp2, 'Cardiologist')

        # Filter by department with no match
        resp3 = self.client.get(url, {'department': self.neurology.id})
        self.assertNotContains(resp3, 'Dr. Sarah Connor')

    def test_admin_toggle_doctor_active_post_only(self):
        url = reverse('doctors:toggle_doctor_active', kwargs={'pk': self.doctor.pk})
        
        self.client.login(username='hospital_admin', password='Password123!')
        # GET should be rejected (Method Not Allowed)
        get_resp = self.client.get(url)
        self.assertEqual(get_resp.status_code, 405)

        # POST toggles is_active
        post_resp = self.client.post(url)
        self.assertRedirects(post_resp, reverse('doctors:manage_doctors'))
        self.doctor.refresh_from_db()
        self.assertFalse(self.doctor.is_active)
