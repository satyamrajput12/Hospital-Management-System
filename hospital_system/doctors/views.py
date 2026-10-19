from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404

from accounts.forms import DoctorRegistrationForm
from accounts.models import User
from departments.models import Department
from .models import Doctor, DoctorAvailability
from .forms import DoctorProfileForm, DoctorAvailabilityForm


def is_admin(user):
    return user.is_authenticated and (user.is_superuser or user.is_admin_role())


def doctor_list(request):
    doctors = Doctor.objects.filter(is_active=True).select_related('user', 'department')
    department_id = request.GET.get('department')
    if department_id:
        doctors = doctors.filter(department_id=department_id)
    departments = Department.objects.filter(is_active=True)
    return render(request, 'doctors/doctor_list.html', {
        'doctors': doctors,
        'departments': departments,
        'selected_department': department_id,
    })


def doctor_detail(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk, is_active=True)
    availabilities = doctor.availabilities.all()
    return render(request, 'doctors/doctor_detail.html', {
        'doctor': doctor,
        'availabilities': availabilities,
    })


@login_required
@user_passes_test(is_admin)
def add_doctor(request):
    if request.method == 'POST':
        user_form = DoctorRegistrationForm(request.POST)
        profile_form = DoctorProfileForm(request.POST)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            doctor = profile_form.save(commit=False)
            doctor.user = user
            doctor.save()
            messages.success(request, f'Doctor {user.get_full_name()} added successfully.')
            return redirect('doctors:manage_list')
    else:
        user_form = DoctorRegistrationForm()
        profile_form = DoctorProfileForm()
    return render(request, 'doctors/add_doctor.html', {
        'user_form': user_form,
        'profile_form': profile_form,
    })


@login_required
@user_passes_test(is_admin)
def manage_doctor_list(request):
    doctors = Doctor.objects.select_related('user', 'department').all()
    return render(request, 'doctors/manage_doctor_list.html', {'doctors': doctors})


@login_required
@user_passes_test(is_admin)
def toggle_doctor_active(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    doctor.is_active = not doctor.is_active
    doctor.save()
    messages.success(request, f"Doctor status updated to {'Active' if doctor.is_active else 'Inactive'}.")
    return redirect('doctors:manage_list')


@login_required
def doctor_availability_manage(request):
    """Allow logged-in doctor to manage their own availability slots."""
    doctor = get_object_or_404(Doctor, user=request.user)
    if request.method == 'POST':
        form = DoctorAvailabilityForm(request.POST)
        if form.is_valid():
            availability = form.save(commit=False)
            availability.doctor = doctor
            availability.save()
            messages.success(request, 'Availability slot added.')
            return redirect('doctors:availability_manage')
    else:
        form = DoctorAvailabilityForm()
    slots = doctor.availabilities.all()
    return render(request, 'doctors/availability_manage.html', {'form': form, 'slots': slots, 'doctor': doctor})


@login_required
def delete_availability(request, pk):
    slot = get_object_or_404(DoctorAvailability, pk=pk, doctor__user=request.user)
    slot.delete()
    messages.success(request, 'Availability slot removed.')
    return redirect('doctors:availability_manage')
