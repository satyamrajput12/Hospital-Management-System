# Hospital Management System

A complete hospital appointment booking and management system built with Django. Supports three roles — **Patients**, **Doctors**, and **Admins** — each with tailored dashboards, availability scheduling, and appointment workflows.

## Features

- **Patients**
  - Self-registration and login
  - Browse departments and doctors, view doctor profiles and availability
  - Book appointments with a chosen doctor, date, time, and reason
  - View and cancel their own appointments
  - Edit personal profile

- **Doctors**
  - Secure login (accounts created by admin)
  - View incoming appointment requests, filter by status
  - Confirm, complete, or cancel appointments and add consultation notes
  - Manage weekly availability slots

- **Admin**
  - Full Django admin panel for Departments, Doctors, Availability, Appointments, and Users
  - Custom "Add Doctor" flow that creates both the user account and doctor profile
  - Analytics dashboard with stats (total doctors, departments, appointments, pending requests)
  - View and filter all appointments system-wide

- **Design & UI**
  - Clean, responsive Bootstrap 5 interface
  - Role-based dashboard redirect after authentication
  - Sample data seeding command included

## Project Structure

```
hospital_appointment_system/
├── hospital_system/
│   ├── accounts/         # Custom User model (role: ADMIN/DOCTOR/PATIENT), auth views, profile
│   ├── departments/      # Department model + seed_data management command
│   ├── doctors/          # Doctor & DoctorAvailability models, doctor management views
│   ├── appointments/     # Appointment model, booking & status-update workflows
│   ├── corepages/        # Home page + role-based dashboards
│   ├── templates/        # HTML templates (Bootstrap 5)
│   ├── static/           # CSS & static assets
│   ├── hospital_system/  # Project settings & root urls
│   ├── manage.py         # Django management script
│   └── requirements.txt  # Project dependencies
├── .gitignore
└── README.md
```

## Setup Instructions

1. **Navigate to the project directory**
   ```bash
   cd hospital_system
   ```

2. **Create and activate a virtual environment (recommended)**
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Linux/macOS:
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply migrations**
   ```bash
   python manage.py migrate
   ```

5. **Seed sample data** (creates admin user, departments, and doctors)
   ```bash
   python manage.py seed_data
   ```

6. **Run the development server**
   ```bash
   python manage.py runserver
   ```

7. Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser.

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

Patients can register themselves from the **Register** page on the site.
The Django admin panel is available at [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/).
