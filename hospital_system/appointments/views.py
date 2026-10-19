from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import render, redirect, get_object_or_404

from doctors.models import Doctor
from .forms import AppointmentForm, AppointmentStatusForm
from .models import Appointment


def is_doctor(user):
    return user.is_authenticated and user.is_doctor_role()


def is_patient(user):
    return user.is_authenticated and user.is_patient_role()


@login_required
@user_passes_test(is_patient, login_url='core:redirect_dashboard')
def book_appointment(request, doctor_pk):
    doctor = get_object_or_404(Doctor, pk=doctor_pk, is_active=True)
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.doctor = doctor
            appointment.patient = request.user
            already_booked = Appointment.objects.filter(
                doctor=doctor,
                appointment_date=appointment.appointment_date,
                appointment_time=appointment.appointment_time,
            ).exclude(status=Appointment.Status.CANCELLED).exists()
            if already_booked:
                form.add_error(None, 'This time slot is already booked. Please choose another time.')
            else:
                try:
                    appointment.save()
                    messages.success(request, 'Appointment requested successfully! You will be notified once confirmed.')
                    return redirect('appointments:my_appointments')
                except IntegrityError:
                    form.add_error(None, 'This time slot is already booked. Please choose another time.')
    else:
        initial = {}
        if request.GET.get('date'):
            initial['appointment_date'] = request.GET.get('date')
        if request.GET.get('time'):
            initial['appointment_time'] = request.GET.get('time')
        form = AppointmentForm(initial=initial)
    return render(request, 'appointments/book_appointment.html', {'form': form, 'doctor': doctor})


@login_required
@user_passes_test(is_patient, login_url='core:redirect_dashboard')
def my_appointments(request):
    appointments = Appointment.objects.filter(patient=request.user).select_related('doctor__user')
    return render(request, 'appointments/my_appointments.html', {'appointments': appointments})


@login_required
@user_passes_test(is_patient, login_url='core:redirect_dashboard')
def cancel_appointment(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk, patient=request.user)
    if appointment.can_cancel():
        appointment.status = Appointment.Status.CANCELLED
        appointment.save()
        messages.success(request, 'Appointment cancelled.')
    else:
        messages.error(request, 'This appointment cannot be cancelled.')
    return redirect('appointments:my_appointments')


@login_required
@user_passes_test(is_doctor, login_url='core:redirect_dashboard')
def doctor_appointments(request):
    doctor = get_object_or_404(Doctor, user=request.user)
    status_filter = request.GET.get('status')
    appointments = Appointment.objects.filter(doctor=doctor).select_related('patient')
    if status_filter:
        appointments = appointments.filter(status=status_filter)
    return render(request, 'appointments/doctor_appointments.html', {
        'appointments': appointments,
        'status_choices': Appointment.Status.choices,
        'status_filter': status_filter,
    })


@login_required
@user_passes_test(is_doctor, login_url='core:redirect_dashboard')
def update_appointment_status(request, pk):
    doctor = get_object_or_404(Doctor, user=request.user)
    appointment = get_object_or_404(Appointment, pk=pk, doctor=doctor)
    if request.method == 'POST':
        form = AppointmentStatusForm(request.POST, instance=appointment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Appointment updated.')
            return redirect('appointments:doctor_appointments')
    else:
        form = AppointmentStatusForm(instance=appointment)
    return render(request, 'appointments/update_status.html', {'form': form, 'appointment': appointment})


@login_required
def all_appointments_admin(request):
    if not (request.user.is_superuser or request.user.is_admin_role()):
        return redirect('core:redirect_dashboard')
    appointments = Appointment.objects.select_related('doctor__user', 'patient').all()
    status_filter = request.GET.get('status')
    if status_filter:
        appointments = appointments.filter(status=status_filter)
    return render(request, 'appointments/all_appointments.html', {
        'appointments': appointments,
        'status_choices': Appointment.Status.choices,
        'status_filter': status_filter,
    })
