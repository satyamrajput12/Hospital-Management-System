import datetime
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from departments.models import Department, LabTest, LabBooking

User = get_user_model()


class DepartmentAndLabTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.dept = Department.objects.create(name='Pathology', description='Clinical lab testing')
        
        self.lab_test = LabTest.objects.create(
            name='Complete Blood Count (CBC)',
            department=self.dept,
            description='Routine blood panel analysis',
            price=Decimal('500.00'),
            discount_price=Decimal('400.00'),
            duration='12 hours',
            sample_type='Blood',
            is_active=True
        )

        self.patient = User.objects.create_user(
            username='lab_patient',
            email='patient@lab.com',
            password='Password123!',
            role=User.Role.PATIENT,
            is_email_verified=True,
            is_active=True
        )

        self.admin = User.objects.create_user(
            username='lab_admin',
            email='admin@lab.com',
            password='Password123!',
            role=User.Role.ADMIN,
            is_staff=True,
            is_email_verified=True,
            is_active=True
        )

    def test_lab_test_pricing_and_discounts(self):
        # Effective price should reflect discount
        self.assertEqual(self.lab_test.effective_price(), Decimal('400.00'))
        self.assertEqual(self.lab_test.discount_percentage(), 20)

        # Without discount
        self.lab_test.discount_price = None
        self.assertEqual(self.lab_test.effective_price(), Decimal('500.00'))
        self.assertEqual(self.lab_test.discount_percentage(), 0)

    def test_public_lab_test_catalog_and_detail(self):
        list_url = reverse('departments:lab_test_list')
        resp = self.client.get(list_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Complete Blood Count (CBC)')

        detail_url = reverse('departments:lab_test_detail', kwargs={'pk': self.lab_test.pk})
        resp2 = self.client.get(detail_url)
        self.assertEqual(resp2.status_code, 200)
        self.assertContains(resp2, 'Blood')

    def test_book_lab_test_records_server_price(self):
        self.client.login(username='lab_patient', password='Password123!')
        book_url = reverse('departments:book_lab_test', kwargs={'pk': self.lab_test.pk})
        
        future_date = (datetime.date.today() + datetime.timedelta(days=2)).isoformat()
        resp = self.client.post(book_url, {
            'appointment_date': future_date,
            'time_slot': '08:00 AM - 10:00 AM',
            'collection_type': 'HOME',
            'collection_address': '123 Baker Street, Suite 4',
            'patient_phone': '9876543210',
            'notes': 'Please ring the doorbell upon arrival.',
        })
        self.assertRedirects(resp, reverse('departments:my_lab_bookings'))

        booking = LabBooking.objects.get(patient=self.patient, test=self.lab_test)
        self.assertEqual(booking.status, LabBooking.Status.PENDING)
        self.assertEqual(booking.price_charged, Decimal('400.00'))
        self.assertEqual(booking.collection_type, 'HOME')

    def test_patient_can_cancel_lab_booking_via_post(self):
        booking = LabBooking.objects.create(
            patient=self.patient,
            test=self.lab_test,
            appointment_date=datetime.date.today() + datetime.timedelta(days=3),
            price_charged=Decimal('400.00'),
            status=LabBooking.Status.PENDING
        )
        cancel_url = reverse('departments:cancel_lab_booking', kwargs={'pk': booking.pk})

        self.client.login(username='lab_patient', password='Password123!')
        # Reject GET
        resp_get = self.client.get(cancel_url)
        self.assertEqual(resp_get.status_code, 405)

        # Allow POST
        resp_post = self.client.post(cancel_url)
        self.assertRedirects(resp_post, reverse('departments:my_lab_bookings'))
        booking.refresh_from_db()
        self.assertEqual(booking.status, LabBooking.Status.CANCELLED)

    def test_admin_lab_booking_management(self):
        booking = LabBooking.objects.create(
            patient=self.patient,
            test=self.lab_test,
            appointment_date=datetime.date.today() + datetime.timedelta(days=1),
            price_charged=Decimal('400.00'),
            status=LabBooking.Status.PENDING
        )
        update_url = reverse('departments:admin_lab_booking_update', kwargs={'pk': booking.pk})

        self.client.login(username='lab_admin', password='Password123!')
        resp = self.client.post(update_url, {
            'status': LabBooking.Status.CONFIRMED,
            'notes': 'Phlebotomist scheduled for 09:30 AM',
        })
        self.assertRedirects(resp, reverse('departments:admin_lab_booking_list'))
        booking.refresh_from_db()
        self.assertEqual(booking.status, LabBooking.Status.CONFIRMED)
