from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from departments.models import Department
from doctors.models import Doctor
from appointments.models import Appointment


def home(request):
    departments = Department.objects.filter(is_active=True)[:6]
    doctors = Doctor.objects.filter(is_active=True).select_related('user', 'department')[:6]
    return render(request, 'corepages/home.html', {
        'departments': departments,
        'doctors': doctors,
    })


@login_required
def redirect_dashboard(request):
    user = request.user
    if user.is_superuser or user.is_admin_role():
        return redirect('core:admin_dashboard')
    elif user.is_doctor_role():
        return redirect('core:doctor_dashboard')
    else:
        return redirect('core:patient_dashboard')


@login_required
def patient_dashboard(request):
    appointments = Appointment.objects.filter(patient=request.user).select_related('doctor__user')[:5]
    upcoming_count = Appointment.objects.filter(
        patient=request.user, status__in=['PENDING', 'CONFIRMED']
    ).count()
    return render(request, 'corepages/patient_dashboard.html', {
        'appointments': appointments,
        'upcoming_count': upcoming_count,
    })


@login_required
def doctor_dashboard(request):
    doctor = getattr(request.user, 'doctor_profile', None)
    appointments = []
    pending_count = confirmed_count = 0
    if doctor:
        appointments = Appointment.objects.filter(doctor=doctor).select_related('patient')[:5]
        pending_count = Appointment.objects.filter(doctor=doctor, status='PENDING').count()
        confirmed_count = Appointment.objects.filter(doctor=doctor, status='CONFIRMED').count()
    return render(request, 'corepages/doctor_dashboard.html', {
        'doctor': doctor,
        'appointments': appointments,
        'pending_count': pending_count,
        'confirmed_count': confirmed_count,
    })


@login_required
def admin_dashboard(request):
    if not (request.user.is_superuser or request.user.is_admin_role()):
        return redirect('core:redirect_dashboard')
    stats = {
        'total_doctors': Doctor.objects.count(),
        'total_departments': Department.objects.count(),
        'total_appointments': Appointment.objects.count(),
        'pending_appointments': Appointment.objects.filter(status='PENDING').count(),
    }
    recent_appointments = Appointment.objects.select_related('doctor__user', 'patient').all()[:8]
    return render(request, 'corepages/admin_dashboard.html', {
        'stats': stats,
        'recent_appointments': recent_appointments,
    })
