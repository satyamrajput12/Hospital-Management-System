# City Care Hospital — Appointment System (Django)

A complete hospital appointment booking system built with Django. Supports three roles —
**Patients**, **Doctors**, and **Admins** — each with their own dashboard and workflows.

## Features

- **Patients**
  - Self-registration and login
  - Browse departments and doctors, view doctor profiles and availability
  - Book appointments with a chosen doctor, date, time, and reason
  - View and cancel their own appointments
  - Edit personal profile (with optional profile picture)

- **Doctors**
  - Login (accounts created by admin)
  - View incoming appointment requests, filter by status
  - Confirm, complete, or cancel appointments and add consultation notes
  - Manage their own weekly availability slots

- **Admin**
  - Full Django admin panel for Departments, Doctors, Availability, Appointments, Users
  - Custom "Add Doctor" flow that creates both the user account and doctor profile
  - Dashboard with stats (total doctors, departments, appointments, pending requests)
  - View and filter all appointments system-wide

- Role-based dashboard redirect after login
- Clean, responsive Bootstrap 5 UI
- Sample data seeding command (departments, doctors, admin login)

## Project Structure

```
hospital_system/
├── accounts/         # Custom User model (role: ADMIN/DOCTOR/PATIENT), auth views, profile
├── departments/       # Department model + seed_data management command
├── doctors/            # Doctor & DoctorAvailability models, doctor management views
├── appointments/    # Appointment model, booking & status-update workflows
├── corepages/          # Home page + role-based dashboards
├── templates/            # All HTML templates (Bootstrap 5)
├── static/css/         # Custom styling
└── hospital_system/  # Project settings & root urls
```

## Setup Instructions

1. **Create a virtual environment (recommended)**
   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Apply migrations**
   ```bash
   python manage.py migrate
   ```

4. **Seed sample data** (creates an admin user, 6 departments, and 6 doctors)
   ```bash
   python manage.py seed_data
   ```

5. **Run the development server**
   ```bash
   python manage.py runserver
   ```

6. Visit **http://127.0.0.1:8000/**

## Default Login Credentials (after seeding)

| Role   | Username   | Password        |
|--------|------------|-----------------|
| Admin  | `admin`    | `Admin@12345`   |
| Doctor | `drsharma` | `Doctor@12345`  |
| Doctor | `drgupta`  | `Doctor@12345`  |
| Doctor | `drpatel`  | `Doctor@12345`  |
| Doctor | `drmehta`  | `Doctor@12345`  |
| Doctor | `drkhan`   | `Doctor@12345`  |
| Doctor | `drrao`    | `Doctor@12345`  |

Patients register themselves from the **Register** page on the site.

The Django admin panel is available at **http://127.0.0.1:8000/admin/** (login with the admin
credentials above) — use it to manage departments, doctors, availability, and appointments directly.

## Notes for Production Use

This project is configured for local development (`DEBUG=True`, SQLite database, a hardcoded
`SECRET_KEY`). Before deploying to production you should:
- Set `DEBUG = False` and configure `ALLOWED_HOSTS` properly
- Move `SECRET_KEY` and other secrets into environment variables
- Switch to a production-grade database (PostgreSQL, MySQL, etc.)
- Configure static/media file serving (e.g. via WhiteNoise or a CDN)
- Set up HTTPS and other Django security middleware settings
