# Medicare Healthcare Management System (Django 5 / 6)

A production-grade, secure, database-driven healthcare management and appointment booking platform built with Django. Designed around a clean **5-app architecture**, the system provides comprehensive role-based workflows for **Patients**, **Doctors**, and **Hospital Administrators**, featuring a responsive **Medicare-themed Bootstrap 5** user interface, integrated diagnostic lab booking, and an end-to-end persistent pharmacy ordering system.

---

## 🏥 Architecture Overview

The system strictly adheres to separation of concerns across 5 modular Django applications:

| App | Primary Responsibilities |
|---|---|
| **`accounts`** | Custom User model (`ADMIN`, `DOCTOR`, `PATIENT`), cryptographic email verification tokens, secure password reset, profile editing, rate limiting, and role-based access decorators (`@patient_required`, `@doctor_required`, `@admin_required`, `@verified_email_required`). |
| **`doctors`** | Doctor profiles (specialization, qualifications, fee, experience, bio, avatar), weekly availability slot scheduling with overlap conflict prevention, doctor self-profile management, and administrative doctor staff directories. |
| **`departments`** | Clinical specialties catalog, dynamic diagnostic lab tests (`LabTest` with discount and turnaround calculations), patient lab test bookings (`LabBooking` with home collection support), and admin lab management. |
| **`appointments`** | End-to-end appointment lifecycle (booking, doctor availability validation, race-condition double-booking database constraints, rescheduling, and secure POST cancellation), clinical documentation (`MedicalRecord`), electronic prescriptions (`Prescription` & `PrescriptionItem`), and billing invoices (`AppointmentBilling`). |
| **`corepages`** | Landing page, unified multi-entity search, database-backed pharmacy catalog (`Product`, `ProductCategory`), persistent shopping cart (`Cart`, `CartItem`), checkout workflow (`Order`, `OrderItem`), simulated sandbox & Cash on Delivery (COD) payment processing, role dashboards, and custom error handlers (400, 403, 404, 500). |

---

## 🔒 Security Architecture

1. **Role-Based Access Control (RBAC)**: Server-side decorators enforce strict role boundaries. Patients cannot view or modify clinical notes, other patients' records, orders, or appointments.
2. **Insecure Direct Object Reference (IDOR) Protection**: All patient-specific resources (invoices, lab bookings, orders, medical records, prescriptions) enforce ownership checks on the server (`request.user == resource.patient`).
3. **State-Changing POST Protection**: Destructive and state-changing actions (cancellation, status updates, cart modifications, user activations) strictly require `POST` with CSRF tokens.
4. **Environment Secret Management**: No production secrets or API keys are committed in source code. Settings are loaded via `.env` with safe fallbacks and a comprehensive `.env.example`.
5. **Session & Cookie Security**: Configured with `SESSION_COOKIE_HTTPONLY = True`, `SESSION_COOKIE_SAMESITE = 'Lax'`, and production SSL headers (`SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `SESSION_COOKIE_SECURE`).
6. **Double-Booking Race Condition Prevention**: Enforced via atomic database transactions (`select_for_update()`) and an ORM conditional `UniqueConstraint` on active appointments:
   ```python
   models.UniqueConstraint(
       fields=['doctor', 'appointment_date', 'appointment_time'],
       condition=~models.Q(status='CANCELLED'),
       name='unique_active_doctor_appointment_slot'
   )
   ```

---

## 🛠️ Requirements & Installation

### Prerequisites
- Python 3.10+ (tested on Python 3.13)
- SQLite (default development) or PostgreSQL / MySQL (production)
- Modern web browser (Chrome, Firefox, Safari, Edge)

### 1. Clone & Set Up Virtual Environment

```bash
cd hospital_system
python -m venv venv

# On Windows:
venv\Scripts\activate

# On Linux/macOS:
source venv/bin/activate
```

### 2. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create your local `.env` file by copying `.env.example`:

```bash
cp .env.example .env
```

Adjust the following values in `.env` as needed:

```ini
SECRET_KEY=your-secure-random-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

### 4. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Seed Sample Data

The project includes two complementary seeding commands:
1. `seed_data` (Departments and initial clinical staff):
   ```bash
   python manage.py seed_data
   ```
2. `seed_medicare` (Diagnostic lab tests, pharmacy inventory, and doctor schedules):
   ```bash
   python manage.py seed_medicare
   ```

### 6. Create Superuser (Optional)

```bash
python manage.py createsuperuser
```

### 7. Run the Development Server

```bash
python manage.py runserver
```

Visit **http://127.0.0.1:8000/** in your browser.

---

## 👥 Default Demo Credentials (Post-Seed)

| Role | Username | Password | Email |
|---|---|---|---|
| **Admin** | `admin` | `Admin@12345` | `admin@medicare.local` |
| **Doctor** | `drsharma` | `Doctor@12345` | `drsharma@medicare.local` |
| **Doctor** | `drgupta` | `Doctor@12345` | `drgupta@medicare.local` |
| **Doctor** | `drpatel` | `Doctor@12345` | `drpatel@medicare.local` |
| **Patient** | Self-register at `/accounts/register/` or use created test users. |

> [!NOTE]
> For self-registered patients during local testing with `console.EmailBackend`, the verification link is printed directly to the terminal stdout. Click or paste the token link to verify the account.

---

## 🧪 Automated Testing & Quality Assurance

To execute the automated test suite covering authentication, authorization, IDOR protection, appointments, lab tests, cart operations, and inventory consistency:

```bash
python manage.py test
```

To run individual application test suites:

```bash
python manage.py test accounts
python manage.py test doctors
python manage.py test departments
python manage.py test appointments
python manage.py test corepages
```

To verify system integrity and database migrations:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
```

---

## 📑 Role Permissions Matrix

| Feature | Patient | Doctor | Admin |
|---|:---:|:---:|:---:|
| Browse Doctors & Specialties | ✅ | ✅ | ✅ |
| Book Appointment | ✅ (Verified only) | ❌ | ❌ |
| Reschedule / Cancel Own Appointment | ✅ | ❌ | ✅ |
| Accept / Reject / Complete Consultations | ❌ | ✅ (Own patients) | ✅ |
| Create Medical Records & Prescriptions | ❌ | ✅ (Own patients) | ❌ |
| View Released Medical Records & Prescriptions | ✅ (Own records only) | ✅ (Own patients) | ❌ |
| Book Diagnostic Lab Tests | ✅ (Verified only) | ❌ | ❌ |
| Update Lab Booking Status | ❌ | ❌ | ✅ |
| Pharmacy Cart & Checkout | ✅ (Verified only) | ❌ | ❌ |
| Manage Pharmacy Inventory & Orders | ❌ | ❌ | ✅ |
| Manage Staff Accounts & Toggles | ❌ | ❌ | ✅ |

---

## 🚀 Production Deployment Checklist

1. **Environment Variables**:
   - Set `DEBUG=False` in `.env`.
   - Generate a cryptographically strong `SECRET_KEY` (50+ random characters).
   - Configure comma-separated domain names in `ALLOWED_HOSTS` (e.g. `yourhospital.com,www.yourhospital.com`).
2. **HTTPS & Cookies**:
   - Ensure an SSL certificate (e.g., Let's Encrypt) is configured in your web server (Nginx/Caddy).
   - Set `SECURE_SSL_REDIRECT=True` and `SESSION_COOKIE_SECURE=True`.
3. **Database**:
   - Configure PostgreSQL or MySQL connection settings in `settings.py`.
4. **Static & Media Files**:
   - Run `python manage.py collectstatic --noinput`.
   - Serve static assets using Nginx or WhiteNoise.
   - For uploaded doctor avatars and medical files, configure protected object storage (AWS S3, Google Cloud Storage, or private media volume).
5. **Transactional Email**:
   - Configure a real transactional email provider (SMTP relay, SendGrid, Amazon SES, or Postmark) in `.env` (`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`).

---

## ⚠️ Known Limitations & External Dependencies

1. **Online Payment Gateway**:
   - The application provides a fully functioning development **Cash on Delivery (COD)** and **Simulated Card Sandbox Mode** that exercises all order state changes, inventory locks, and payment transaction logs without requiring third-party credentials.
   - Integrating live gateways (Stripe, Razorpay, or PayPal) requires obtaining merchant API keys and configuring webhook endpoints.
2. **SMS Gateway**:
   - Notifications currently use transactional emails. SMS appointment reminders require configuring a provider like Twilio or AWS SNS.
