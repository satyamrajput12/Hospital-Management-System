from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from accounts.decorators import admin_required, patient_required, verified_email_required
from doctors.models import Doctor
from .forms import DepartmentForm, LabTestForm, LabBookingForm, LabBookingStatusForm
from .models import Department, LabTest, LabBooking


def department_list(request):
    departments = Department.objects.filter(is_active=True).annotate(
        doctor_count=Count('doctors', filter=Q(doctors__is_active=True)),
        test_count=Count('lab_tests', filter=Q(lab_tests__is_active=True))
    )
    return render(request, 'departments/department_list.html', {'departments': departments})


def department_detail(request, pk):
    department = get_object_or_404(Department, pk=pk, is_active=True)
    doctors = Doctor.objects.filter(department=department, is_active=True).select_related('user')
    lab_tests = department.lab_tests.filter(is_active=True)
    return render(request, 'departments/department_detail.html', {
        'department': department,
        'doctors': doctors,
        'lab_tests': lab_tests,
    })


def lab_test_list(request):
    """
    Search and filter hospital diagnostic lab tests.
    """
    tests = LabTest.objects.filter(is_active=True).select_related('department')

    query = request.GET.get('q', '').strip()
    dept_id = request.GET.get('department', '').strip()
    sample_filter = request.GET.get('sample', '').strip()

    if query:
        tests = tests.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(sample_type__icontains=query)
        )

    if dept_id:
        tests = tests.filter(department_id=dept_id)

    if sample_filter:
        tests = tests.filter(sample_type__icontains=sample_filter)

    paginator = Paginator(tests, 9)
    page_obj = paginator.get_page(request.GET.get('page'))

    departments = Department.objects.filter(is_active=True)

    return render(request, 'departments/lab_test_list.html', {
        'page_obj': page_obj,
        'departments': departments,
        'query': query,
        'selected_department': dept_id,
        'selected_sample': sample_filter,
        'total_tests': paginator.count,
    })


def lab_test_detail(request, pk):
    test = get_object_or_404(LabTest, pk=pk, is_active=True)
    related_tests = LabTest.objects.filter(
        department=test.department,
        is_active=True
    ).exclude(pk=test.pk)[:3]
    return render(request, 'departments/lab_test_detail.html', {
        'test': test,
        'related_tests': related_tests,
    })


@patient_required
@verified_email_required
def book_lab_test(request, pk):
    """
    Patient books a lab diagnostic test with validated server-side price.
    """
    test = get_object_or_404(LabTest, pk=pk, is_active=True)

    if request.method == 'POST':
        form = LabBookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.patient = request.user
            booking.test = test
            booking.price_charged = test.effective_price()
            booking.status = LabBooking.Status.PENDING
            booking.save()

            messages.success(
                request,
                f"Diagnostic booking requested for '{test.name}' on {booking.appointment_date}. "
                "Our lab coordination team will contact you shortly."
            )
            return redirect('departments:my_lab_bookings')
    else:
        initial = {
            'collection_address': request.user.address,
            'patient_phone': request.user.phone,
        }
        form = LabBookingForm(initial=initial)

    return render(request, 'departments/book_lab_test.html', {
        'form': form,
        'test': test,
    })


@patient_required
def my_lab_bookings(request):
    """
    Patient view of their diagnostic lab bookings history.
    """
    bookings = LabBooking.objects.filter(patient=request.user).select_related('test').order_by('-appointment_date', '-created_at')
    paginator = Paginator(bookings, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'departments/my_lab_bookings.html', {
        'page_obj': page_obj,
        'total_bookings': paginator.count,
    })


@patient_required
@require_POST
def cancel_lab_booking(request, pk):
    """
    Cancel an existing lab booking via POST.
    """
    booking = get_object_or_404(LabBooking, pk=pk, patient=request.user)
    if booking.can_cancel():
        booking.status = LabBooking.Status.CANCELLED
        booking.save()
        messages.success(request, f"Lab booking for '{booking.test.name}' has been cancelled.")
    else:
        messages.error(request, "This lab booking cannot be cancelled because it is completed or already cancelled.")
    return redirect('departments:my_lab_bookings')


# ==============================================================================
# ADMIN LAB & DEPARTMENT MANAGEMENT VIEWS
# ==============================================================================

@admin_required
def admin_department_list(request):
    departments = Department.objects.annotate(
        doctor_count=Count('doctors'),
        test_count=Count('lab_tests')
    ).order_by('name')
    return render(request, 'departments/admin_department_list.html', {'departments': departments})


@admin_required
def admin_department_add(request):
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            dept = form.save()
            messages.success(request, f"Department '{dept.name}' created successfully.")
            return redirect('departments:admin_list')
    else:
        form = DepartmentForm()
    return render(request, 'departments/admin_department_form.html', {'form': form, 'title': 'Add New Department'})


@admin_required
def admin_department_edit(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=dept)
        if form.is_valid():
            form.save()
            messages.success(request, f"Department '{dept.name}' updated successfully.")
            return redirect('departments:admin_list')
    else:
        form = DepartmentForm(instance=dept)
    return render(request, 'departments/admin_department_form.html', {'form': form, 'title': f"Edit {dept.name}", 'dept': dept})


@admin_required
@require_POST
def admin_department_toggle(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    dept.is_active = not dept.is_active
    dept.save()
    status_str = "activated" if dept.is_active else "deactivated"
    messages.success(request, f"Department '{dept.name}' has been {status_str}.")
    return redirect('departments:admin_list')


@admin_required
def admin_lab_test_list(request):
    tests = LabTest.objects.select_related('department').order_by('name')
    return render(request, 'departments/admin_lab_test_list.html', {'tests': tests})


@admin_required
def admin_lab_test_add(request):
    if request.method == 'POST':
        form = LabTestForm(request.POST, request.FILES)
        if form.is_valid():
            test = form.save()
            messages.success(request, f"Lab Test '{test.name}' added successfully.")
            return redirect('departments:admin_lab_test_list')
    else:
        form = LabTestForm()
    return render(request, 'departments/admin_lab_test_form.html', {'form': form, 'title': 'Add Diagnostic Test'})


@admin_required
def admin_lab_test_edit(request, pk):
    test = get_object_or_404(LabTest, pk=pk)
    if request.method == 'POST':
        form = LabTestForm(request.POST, request.FILES, instance=test)
        if form.is_valid():
            form.save()
            messages.success(request, f"Lab Test '{test.name}' updated successfully.")
            return redirect('departments:admin_lab_test_list')
    else:
        form = LabTestForm(instance=test)
    return render(request, 'departments/admin_lab_test_form.html', {'form': form, 'title': f"Edit {test.name}", 'test': test})


@admin_required
@require_POST
def admin_lab_test_toggle(request, pk):
    test = get_object_or_404(LabTest, pk=pk)
    test.is_active = not test.is_active
    test.save()
    status_str = "activated" if test.is_active else "deactivated"
    messages.success(request, f"Lab Test '{test.name}' has been {status_str}.")
    return redirect('departments:admin_lab_test_list')


@admin_required
def admin_lab_booking_list(request):
    status_filter = request.GET.get('status', '').strip()
    bookings = LabBooking.objects.select_related('patient', 'test').order_by('-appointment_date')
    if status_filter:
        bookings = bookings.filter(status=status_filter)

    paginator = Paginator(bookings, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'departments/admin_lab_booking_list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'status_choices': LabBooking.Status.choices,
    })


@admin_required
def admin_lab_booking_update(request, pk):
    booking = get_object_or_404(LabBooking, pk=pk)
    if request.method == 'POST':
        form = LabBookingStatusForm(request.POST, instance=booking)
        if form.is_valid():
            form.save()
            messages.success(request, f"Status updated for booking #{booking.pk}.")
            return redirect('departments:admin_lab_booking_list')
    else:
        form = LabBookingStatusForm(instance=booking)
    return render(request, 'departments/admin_lab_booking_update.html', {'form': form, 'booking': booking})
