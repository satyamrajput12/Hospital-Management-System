from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from accounts.decorators import doctor_required, admin_required
from accounts.forms import DoctorRegistrationForm
from accounts.models import User
from departments.models import Department
from .forms import DoctorProfileForm, DoctorSelfProfileForm, DoctorAvailabilityForm
from .models import Doctor, DoctorAvailability, DAYS_OF_WEEK


def doctor_list(request):
    """
    Search and filter certified doctors with pagination and preserving filters.
    """
    doctors = Doctor.objects.filter(is_active=True).select_related('user', 'department')
    
    query = request.GET.get('q', '').strip()
    department_id = request.GET.get('department', '').strip()
    day_of_week = request.GET.get('day', '').strip()
    max_fee = request.GET.get('max_fee', '').strip()
    sort_by = request.GET.get('sort', '').strip()

    if query:
        doctors = doctors.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(specialization__icontains=query) |
            Q(qualification__icontains=query) |
            Q(bio__icontains=query) |
            Q(department__name__icontains=query)
        )

    if department_id:
        doctors = doctors.filter(department_id=department_id)

    if day_of_week:
        doctors = doctors.filter(availabilities__day_of_week=day_of_week).distinct()

    if max_fee:
        try:
            doctors = doctors.filter(consultation_fee__lte=float(max_fee))
        except ValueError:
            pass

    if sort_by == 'fee_low':
        doctors = doctors.order_by('consultation_fee')
    elif sort_by == 'fee_high':
        doctors = doctors.order_by('-consultation_fee')
    elif sort_by == 'experience':
        doctors = doctors.order_by('-experience_years')
    else:
        doctors = doctors.order_by('user__first_name', 'user__last_name')

    paginator = Paginator(doctors, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    departments = Department.objects.filter(is_active=True)

    return render(request, 'doctors/doctor_list.html', {
        'page_obj': page_obj,
        'doctors': page_obj,
        'departments': departments,
        'days_of_week': DAYS_OF_WEEK,
        'selected_department': department_id,
        'selected_day': day_of_week,
        'selected_max_fee': max_fee,
        'selected_sort': sort_by,
        'query': query,
        'total_doctors': paginator.count,
    })


def doctor_detail(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk, is_active=True)
    availabilities = doctor.availabilities.all().order_by('day_of_week', 'start_time')
    return render(request, 'doctors/doctor_detail.html', {
        'doctor': doctor,
        'availabilities': availabilities,
    })


@doctor_required
def doctor_profile_edit(request):
    """
    Allows logged-in doctor to edit their clinical profile and contact details.
    """
    doctor = get_object_or_404(Doctor, user=request.user)
    if request.method == 'POST':
        form = DoctorSelfProfileForm(request.POST, request.FILES, instance=doctor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your doctor profile has been updated successfully.')
            return redirect('doctors:profile_edit')
    else:
        form = DoctorSelfProfileForm(instance=doctor)
    return render(request, 'doctors/doctor_profile_edit.html', {
        'form': form,
        'doctor': doctor,
    })


@admin_required
def add_doctor(request):
    if request.method == 'POST':
        user_form = DoctorRegistrationForm(request.POST)
        profile_form = DoctorProfileForm(request.POST)
        if user_form.is_valid() and profile_form.is_valid():
            with transaction.atomic():
                user = user_form.save()
                doctor = profile_form.save(commit=False)
                doctor.user = user
                doctor.save()
            messages.success(request, f'Doctor Dr. {user.get_full_name()} added successfully.')
            return redirect('doctors:manage_list')
    else:
        user_form = DoctorRegistrationForm()
        profile_form = DoctorProfileForm()
    return render(request, 'doctors/add_doctor.html', {
        'user_form': user_form,
        'profile_form': profile_form,
    })


@admin_required
def admin_edit_doctor(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    if request.method == 'POST':
        profile_form = DoctorProfileForm(request.POST, instance=doctor)
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, f"Profile for Dr. {doctor.user.get_full_name()} updated.")
            return redirect('doctors:manage_list')
    else:
        profile_form = DoctorProfileForm(instance=doctor)
    return render(request, 'doctors/edit_doctor_admin.html', {
        'doctor': doctor,
        'profile_form': profile_form,
    })


@admin_required
def manage_doctor_list(request):
    doctors = Doctor.objects.select_related('user', 'department').all().order_by('user__first_name')
    query = request.GET.get('q', '').strip()
    if query:
        doctors = doctors.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(specialization__icontains=query) |
            Q(department__name__icontains=query)
        )
    return render(request, 'doctors/manage_doctor_list.html', {
        'doctors': doctors,
        'query': query,
    })


@admin_required
@require_POST
def toggle_doctor_active(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    doctor.is_active = not doctor.is_active
    doctor.save()
    status_label = 'Active' if doctor.is_active else 'Inactive'
    messages.success(request, f"Doctor Dr. {doctor.user.get_full_name()} status updated to {status_label}.")
    return redirect('doctors:manage_list')


@doctor_required
def doctor_availability_manage(request):
    """
    Allows a doctor to manage their weekly consultation availability slots.
    """
    doctor = get_object_or_404(Doctor, user=request.user)
    if request.method == 'POST':
        form = DoctorAvailabilityForm(request.POST, doctor=doctor)
        if form.is_valid():
            availability = form.save(commit=False)
            availability.doctor = doctor
            availability.save()
            messages.success(request, 'Availability slot added successfully.')
            return redirect('doctors:availability_manage')
    else:
        form = DoctorAvailabilityForm(doctor=doctor)

    slots = doctor.availabilities.all().order_by('day_of_week', 'start_time')
    return render(request, 'doctors/availability_manage.html', {
        'form': form,
        'slots': slots,
        'doctor': doctor,
    })


@doctor_required
@require_POST
def delete_availability(request, pk):
    slot = get_object_or_404(DoctorAvailability, pk=pk, doctor__user=request.user)
    slot.delete()
    messages.success(request, 'Availability slot removed.')
    return redirect('doctors:availability_manage')
