import datetime
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from departments.models import Department
from doctors.models import Doctor, DoctorAvailability
from appointments.models import (
    Appointment, AppointmentBilling, MedicalRecord, Prescription, PrescriptionItem
)

User = get_user_model()


class AppointmentLifecycleAndClinicalTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.dept = Department.objects.create(name='Cardiology')

        # Doctor
        self.doc_user = User.objects.create_user(
            username='doctor_jones',
            email='jones@hospital.com',
            password='DocPassword123!',
            first_name='Indiana',
            last_name='Jones',
            role=User.Role.DOCTOR,
            is_email_verified=True,
            is_active=True
        )
        self.doctor = Doctor.objects.create(
            user=self.doc_user,
            department=self.dept,
            specialization='Cardiologist',
            consultation_fee=Decimal('250.00'),
            is_active=True
        )
        # Availability: Mondays 09:00 - 12:00
        DoctorAvailability.objects.create(
            doctor=self.doctor,
            day_of_week='MON',
            start_time=datetime.time(9, 0),
            end_time=datetime.time(12, 0),
            slot_duration_minutes=30
        )

        # Patient 1
        self.patient1 = User.objects.create_user(
            username='patient_alice',
            email='alice@hospital.com',
            password='Password123!',
            first_name='Alice',
            last_name='Smith',
            role=User.Role.PATIENT,
            is_email_verified=True,
            is_active=True
        )

        # Patient 2 (for authorization / IDOR tests)
        self.patient2 = User.objects.create_user(
            username='patient_bob',
            email='bob@hospital.com',
            password='Password123!',
            first_name='Bob',
            last_name='Brown',
            role=User.Role.PATIENT,
            is_email_verified=True,
            is_active=True
        )

        # A specific upcoming Monday
        today = datetime.date.today()
        days_ahead = (0 - today.weekday()) % 7  # 0 is Monday
        if days_ahead == 0:
            days_ahead = 7
        self.valid_monday = today + datetime.timedelta(days=days_ahead)

    def test_book_appointment_success_and_invoice_generated(self):
        self.client.login(username='patient_alice', password='Password123!')
        book_url = reverse('appointments:book', kwargs={'doctor_pk': self.doctor.pk})
        
        post_data = {
            'appointment_date': self.valid_monday.isoformat(),
            'appointment_time': '09:00:00',
            'reason': 'Routine heart checkup',
        }
        resp = self.client.post(book_url, post_data)
        self.assertRedirects(resp, reverse('appointments:my_appointments'))

        appt = Appointment.objects.get(patient=self.patient1, doctor=self.doctor)
        self.assertEqual(appt.status, Appointment.Status.PENDING)
        
        # Verify invoice record generated
        billing = AppointmentBilling.objects.get(appointment=appt)
        self.assertEqual(billing.consultation_fee, Decimal('250.00'))
        self.assertEqual(billing.payment_status, AppointmentBilling.PaymentStatus.PENDING)

    def test_double_booking_prevention_at_database_level(self):
        # Create first appointment
        Appointment.objects.create(
            patient=self.patient1,
            doctor=self.doctor,
            appointment_date=self.valid_monday,
            appointment_time=datetime.time(9, 0),
            reason='Initial booking',
            status=Appointment.Status.CONFIRMED
        )

        # Second appointment at exact same time with same doctor must raise IntegrityError
        with self.assertRaises(IntegrityError):
            Appointment.objects.create(
                patient=self.patient2,
                doctor=self.doctor,
                appointment_date=self.valid_monday,
                appointment_time=datetime.time(9, 0),
                reason='Conflicting booking attempt',
                status=Appointment.Status.CONFIRMED
            )

    def test_cancel_appointment_requires_post_and_waives_billing(self):
        appt = Appointment.objects.create(
            patient=self.patient1,
            doctor=self.doctor,
            appointment_date=self.valid_monday,
            appointment_time=datetime.time(10, 0),
            status=Appointment.Status.CONFIRMED
        )
        billing = AppointmentBilling.objects.create(
            appointment=appt,
            patient=self.patient1,
            invoice_number='INV-TEST-CANCEL-01',
            consultation_fee=Decimal('250.00'),
            total_amount=Decimal('262.50'),
            payment_status=AppointmentBilling.PaymentStatus.PENDING
        )

        cancel_url = reverse('appointments:cancel', kwargs={'pk': appt.pk})
        
        self.client.login(username='patient_alice', password='Password123!')
        # Reject GET
        resp_get = self.client.get(cancel_url)
        self.assertEqual(resp_get.status_code, 405)

        # Allow POST
        resp_post = self.client.post(cancel_url)
        self.assertRedirects(resp_post, reverse('appointments:my_appointments'))
        
        appt.refresh_from_db()
        billing.refresh_from_db()
        self.assertEqual(appt.status, Appointment.Status.CANCELLED)
        self.assertEqual(billing.payment_status, AppointmentBilling.PaymentStatus.WAIVED)

    def test_patient_cannot_cancel_or_reschedule_other_patients_appointment(self):
        appt = Appointment.objects.create(
            patient=self.patient1,
            doctor=self.doctor,
            appointment_date=self.valid_monday,
            appointment_time=datetime.time(10, 0),
            status=Appointment.Status.CONFIRMED
        )
        cancel_url = reverse('appointments:cancel', kwargs={'pk': appt.pk})

        # Login as patient2 (Bob)
        self.client.login(username='patient_bob', password='Password123!')
        resp = self.client.post(cancel_url)
        self.assertEqual(resp.status_code, 403)
        appt.refresh_from_db()
        self.assertEqual(appt.status, Appointment.Status.CONFIRMED)

    def test_doctor_clinical_record_and_prescription_workflow(self):
        appt = Appointment.objects.create(
            patient=self.patient1,
            doctor=self.doctor,
            appointment_date=self.valid_monday,
            appointment_time=datetime.time(10, 0),
            status=Appointment.Status.CONFIRMED
        )

        self.client.login(username='doctor_jones', password='DocPassword123!')

        # Create Medical Record with required title
        med_url = reverse('appointments:create_medical_record', kwargs={'appointment_pk': appt.pk})
        resp = self.client.post(med_url, {
            'title': 'Cardiology Health Check',
            'diagnosis': 'Mild hypertension',
            'symptoms': 'Occasional headaches',
            'treatment_plan': 'Lifestyle modifications and diet control',
            'notes': 'Follow up in 4 weeks',
            'is_released_to_patient': True,
        })
        self.assertRedirects(resp, reverse('appointments:doctor_appointments'))
        self.assertTrue(MedicalRecord.objects.filter(appointment=appt).exists())

        # Create Prescription
        rx_url = reverse('appointments:create_prescription', kwargs={'appointment_pk': appt.pk})
        resp_rx = self.client.post(rx_url, {
            'diagnosis': 'Hypertension Grade 1',
            'instructions': 'Take after food',
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-medicine_name': 'Amlodipine 5mg',
            'items-0-dosage': '5mg',
            'items-0-frequency': 'Once daily morning',
            'items-0-duration': '30 days',
        })
        self.assertRedirects(resp_rx, reverse('appointments:doctor_appointments'))
        self.assertTrue(Prescription.objects.filter(appointment=appt).exists())

    def test_patient_medical_history_idor_protection(self):
        appt = Appointment.objects.create(
            patient=self.patient1,
            doctor=self.doctor,
            appointment_date=self.valid_monday,
            appointment_time=datetime.time(10, 0),
            status=Appointment.Status.COMPLETED
        )
        rec = MedicalRecord.objects.create(
            appointment=appt,
            doctor=self.doctor,
            patient=self.patient1,
            title='Confidential Report',
            diagnosis='Confidential diagnosis',
            is_released_to_patient=True
        )

        view_rec_url = reverse('appointments:view_medical_record', kwargs={'pk': rec.pk})

        # Alice (owner) can view
        self.client.login(username='patient_alice', password='Password123!')
        resp1 = self.client.get(view_rec_url)
        self.assertEqual(resp1.status_code, 200)
        self.assertContains(resp1, 'Confidential diagnosis')

        # Bob (attacker) is forbidden (403)
        self.client.login(username='patient_bob', password='Password123!')
        resp2 = self.client.get(view_rec_url)
        self.assertEqual(resp2.status_code, 403)

    def test_invoice_idor_protection(self):
        appt = Appointment.objects.create(
            patient=self.patient1,
            doctor=self.doctor,
            appointment_date=self.valid_monday,
            appointment_time=datetime.time(10, 0),
            status=Appointment.Status.CONFIRMED
        )
        billing = AppointmentBilling.objects.create(
            appointment=appt,
            patient=self.patient1,
            invoice_number='INV-TEST-001',
            consultation_fee=Decimal('250.00'),
            total_amount=Decimal('262.50'),
            payment_status=AppointmentBilling.PaymentStatus.PENDING
        )
        invoice_url = reverse('appointments:view_invoice', kwargs={'pk': appt.pk})

        # Alice can view
        self.client.login(username='patient_alice', password='Password123!')
        resp1 = self.client.get(invoice_url)
        self.assertEqual(resp1.status_code, 200)
        self.assertContains(resp1, 'INV-TEST-001')

        # Bob is blocked (403)
        self.client.login(username='patient_bob', password='Password123!')
        resp2 = self.client.get(invoice_url)
        self.assertEqual(resp2.status_code, 403)
