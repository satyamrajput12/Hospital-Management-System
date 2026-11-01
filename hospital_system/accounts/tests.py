from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core import mail
from accounts.tokens import account_activation_token

User = get_user_model()


class AuthenticationAndSecurityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.patient_password = 'ValidPassword123!'
        self.patient = User.objects.create_user(
            username='patient_test',
            email='patient@test.com',
            password=self.patient_password,
            first_name='Patient',
            last_name='User',
            role=User.Role.PATIENT,
            is_email_verified=True,
            is_active=True
        )
        self.doctor = User.objects.create_user(
            username='doctor_test',
            email='doctor@test.com',
            password='DocPassword123!',
            first_name='Doctor',
            last_name='User',
            role=User.Role.DOCTOR,
            is_email_verified=True,
            is_active=True
        )
        self.admin = User.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='AdminPassword123!',
            first_name='Admin',
            last_name='User',
            role=User.Role.ADMIN,
            is_email_verified=True,
            is_active=True,
            is_staff=True
        )

    def test_patient_registration_success_and_email_dispatched(self):
        url = reverse('accounts:register')
        data = {
            'username': 'newpatient',
            'first_name': 'Jane',
            'last_name': 'Doe',
            'email': 'jane.doe@example.com',
            'phone': '1234567890',
            'password1': 'SecurePassword123!',
            'password2': 'SecurePassword123!',
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse('corepages:redirect_dashboard'), target_status_code=302)
        
        user = User.objects.get(username='newpatient')
        self.assertEqual(user.role, User.Role.PATIENT)
        self.assertFalse(user.is_email_verified)
        self.assertTrue(user.is_active)
        # Verify an activation email was sent
        self.assertGreaterEqual(len(mail.outbox), 1)
        self.assertIn('Verify your Medicare', mail.outbox[0].subject)

    def test_registration_prevents_role_escalation(self):
        url = reverse('accounts:register')
        data = {
            'username': 'hacker',
            'first_name': 'Bad',
            'last_name': 'Actor',
            'email': 'hacker@example.com',
            'password1': 'SecurePassword123!',
            'password2': 'SecurePassword123!',
            'role': 'ADMIN',  # Malicious escalation attempt
            'is_staff': True,
            'is_superuser': True,
        }
        self.client.post(url, data)
        user = User.objects.get(username='hacker')
        self.assertEqual(user.role, User.Role.PATIENT)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_email_verification_workflow(self):
        unverified_user = User.objects.create_user(
            username='unverified_user',
            email='unverified@example.com',
            password='Password123!',
            role=User.Role.PATIENT,
            is_email_verified=False
        )
        uid = urlsafe_base64_encode(force_bytes(unverified_user.pk))
        token = account_activation_token.make_token(unverified_user)
        
        # Valid verification URL
        verify_url = reverse('accounts:verify_email', kwargs={'uidb64': uid, 'token': token})
        response = self.client.get(verify_url)
        self.assertRedirects(response, reverse('accounts:login'))
        
        unverified_user.refresh_from_db()
        self.assertTrue(unverified_user.is_email_verified)

    def test_email_verification_fails_with_tampered_token(self):
        unverified_user = User.objects.create_user(
            username='unverified_user2',
            email='unverified2@example.com',
            password='Password123!',
            role=User.Role.PATIENT,
            is_email_verified=False
        )
        uid = urlsafe_base64_encode(force_bytes(unverified_user.pk))
        bad_token = 'invalid-token-123'
        verify_url = reverse('accounts:verify_email', kwargs={'uidb64': uid, 'token': bad_token})
        response = self.client.get(verify_url)
        self.assertContains(response, 'Verification Link Expired', status_code=200)
        
        unverified_user.refresh_from_db()
        self.assertFalse(unverified_user.is_email_verified)

    def test_login_by_username_and_email(self):
        login_url = reverse('accounts:login')
        
        # Login with username
        resp = self.client.post(login_url, {'username': 'patient_test', 'password': self.patient_password})
        self.assertEqual(resp.status_code, 302)
        self.client.logout()

        # Login with email
        resp2 = self.client.post(login_url, {'username': 'patient@test.com', 'password': self.patient_password})
        self.assertEqual(resp2.status_code, 302)

    def test_open_redirect_protection(self):
        login_url = reverse('accounts:login') + '?next=https://malicious-site.com/steal'
        resp = self.client.post(login_url, {'username': 'patient_test', 'password': self.patient_password})
        # Should redirect to default dashboard redirector, NOT external url
        self.assertRedirects(resp, reverse('corepages:redirect_dashboard'), target_status_code=302)

    def test_secure_logout_via_post(self):
        self.client.login(username='patient_test', password=self.patient_password)
        resp = self.client.post(reverse('accounts:logout'))
        self.assertRedirects(resp, reverse('core:home'))

    def test_password_change_view_requires_authentication(self):
        url = reverse('accounts:password_change')
        resp = self.client.get(url)
        self.assertRedirects(resp, f"{reverse('accounts:login')}?next={url}")

        self.client.login(username='patient_test', password=self.patient_password)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_admin_patient_list_role_protection(self):
        url = reverse('accounts:admin_patient_list')
        
        # Patient cannot access, redirected to their dashboard with warning
        self.client.login(username='patient_test', password=self.patient_password)
        resp = self.client.get(url)
        self.assertRedirects(resp, reverse('corepages:redirect_dashboard'), target_status_code=302)

        # Admin can access
        self.client.login(username='admin_test', password='AdminPassword123!')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'patient_test')

    def test_toggle_user_active_requires_admin_and_post(self):
        url = reverse('accounts:toggle_user_active', kwargs={'pk': self.patient.id})
        
        # GET should be disallowed
        self.client.login(username='admin_test', password='AdminPassword123!')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 405)

        # POST toggles is_active
        resp = self.client.post(url)
        self.assertRedirects(resp, reverse('accounts:admin_patient_list'))
        self.patient.refresh_from_db()
        self.assertFalse(self.patient.is_active)
