import uuid
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from accounts.decorators import patient_required, doctor_required, admin_required, verified_email_required
from doctors.models import Doctor
from .emails import send_appointment_notification
from .forms import (
    AppointmentForm, AppointmentRescheduleForm, AppointmentStatusForm,
    MedicalRecordForm, PrescriptionForm, PrescriptionItemFormSet
)
from .models import Appointment, MedicalRecord, Prescription, AppointmentBilling


@patient_required
@verified_email_required
def book_appointment(request, doctor_pk):
    """
    Books an appointment with server-side availability validation,
    double-booking protection using DB transactions, and invoice creation.
    """
    doctor = get_object_or_404(Doctor, pk=doctor_pk, is_active=True)

    if request.method == 'POST':
        form = AppointmentForm(request.POST, doctor=doctor)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Server-side lock to prevent race-condition double bookings
                    date = form.cleaned_data['appointment_date']
                    time = form.cleaned_data['appointment_time']

                    # Re-check inside transaction with select_for_update
                    conflict_exists = Appointment.objects.select_for_update().filter(
                        doctor=doctor,
                        appointment_date=date,
                        appointment_time=time
                    ).exclude(status=Appointment.Status.CANCELLED).exists()

                    if conflict_exists:
                        form.add_error('appointment_time', 'This slot was just taken by another patient. Please choose another time.')
                        return render(request, 'appointments/book_appointment.html', {'form': form, 'doctor': doctor})

                    appointment = form.save(commit=False)
                    appointment.doctor = doctor
                    appointment.patient = request.user
                    appointment.status = Appointment.Status.PENDING
                    appointment.save()

                    # Automatically generate initial billing record for transparency
                    fee = doctor.consultation_fee
                    tax = round(fee * Decimal('0.05'), 2)  # 5% service tax
                    total = fee + tax
                    inv_num = f"INV-APT-{appointment.pk}-{uuid.uuid4().hex[:6].upper()}"

                    AppointmentBilling.objects.create(
                        appointment=appointment,
                        patient=request.user,
                        invoice_number=inv_num,
                        consultation_fee=fee,
                        tax_amount=tax,
                        total_amount=total,
                        payment_status=AppointmentBilling.PaymentStatus.PENDING,
                        payment_method='Hospital Front Desk / Cash'
                    )

                # Send email notification outside transaction
                send_appointment_notification(appointment, 'booked')

                messages.success(
                    request,
                    f'Appointment successfully requested with Dr. {doctor.user.get_full_name()} for {appointment.appointment_date} at {appointment.appointment_time.strftime("%I:%M %p")}.'
                )
                return redirect('appointments:my_appointments')

            except IntegrityError:
                form.add_error('appointment_time', 'This time slot is already booked. Please choose another slot.')
    else:
        initial = {}
        if request.GET.get('date'):
            initial['appointment_date'] = request.GET.get('date')
        if request.GET.get('time'):
            initial['appointment_time'] = request.GET.get('time')
        form = AppointmentForm(doctor=doctor, initial=initial)

    availabilities = doctor.availabilities.all().order_by('day_of_week', 'start_time')
    return render(request, 'appointments/book_appointment.html', {
        'form': form,
        'doctor': doctor,
        'availabilities': availabilities,
    })


@patient_required
def my_appointments(request):
    """
    Displays the authenticated patient's appointments with tabs for all, upcoming, completed, and cancelled.
    """
    status_tab = request.GET.get('status', 'all')
    appointments = Appointment.objects.filter(patient=request.user).select_related('doctor__user', 'doctor__department', 'billing')

    if status_tab == 'upcoming':
        appointments = appointments.filter(status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED])
    elif status_tab == 'completed':
        appointments = appointments.filter(status=Appointment.Status.COMPLETED)
    elif status_tab == 'cancelled':
        appointments = appointments.filter(status=Appointment.Status.CANCELLED)

    paginator = Paginator(appointments, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'appointments/my_appointments.html', {
        'page_obj': page_obj,
        'status_tab': status_tab,
        'total_appointments': paginator.count,
    })


@login_required
def reschedule_appointment(request, pk):
    """
    Reschedule an existing pending or confirmed appointment.
    """
    appointment = get_object_or_404(Appointment, pk=pk)

    # Permission check: must be owner patient, assigned doctor, or admin
    is_owner = (appointment.patient == request.user)
    is_doc = (hasattr(request.user, 'doctor_profile') and appointment.doctor == request.user.doctor_profile)
    is_adm = (request.user.is_superuser or request.user.is_admin_role())

    if not (is_owner or is_doc or is_adm):
        raise PermissionDenied("You do not have permission to reschedule this appointment.")

    if not appointment.can_reschedule():
        messages.error(request, "This appointment cannot be rescheduled because it is already completed or cancelled.")
        return redirect('appointments:my_appointments' if is_owner else 'appointments:doctor_appointments')

    if request.method == 'POST':
        form = AppointmentRescheduleForm(request.POST, appointment=appointment)
        if form.is_valid():
            with transaction.atomic():
                appointment.appointment_date = form.cleaned_data['appointment_date']
                appointment.appointment_time = form.cleaned_data['appointment_time']
                reason = form.cleaned_data.get('reschedule_reason', '')
                if reason:
                    appointment.notes = f"{appointment.notes}\n[Rescheduled]: {reason}".strip()
                appointment.save()

            send_appointment_notification(appointment, 'rescheduled')
            messages.success(request, f"Appointment successfully rescheduled to {appointment.appointment_date} at {appointment.appointment_time.strftime('%I:%M %p')}.")

            if is_owner:
                return redirect('appointments:my_appointments')
            return redirect('appointments:doctor_appointments')
    else:
        form = AppointmentRescheduleForm(appointment=appointment)

    return render(request, 'appointments/reschedule_appointment.html', {
        'form': form,
        'appointment': appointment,
    })


@login_required
@require_POST
def cancel_appointment(request, pk):
    """
    Cancels an appointment via secure POST request.
    """
    appointment = get_object_or_404(Appointment, pk=pk)

    is_owner = (appointment.patient == request.user)
    is_doc = (hasattr(request.user, 'doctor_profile') and appointment.doctor == request.user.doctor_profile)
    is_adm = (request.user.is_superuser or request.user.is_admin_role())

    if not (is_owner or is_doc or is_adm):
        raise PermissionDenied("You do not have permission to cancel this appointment.")

    if appointment.can_cancel():
        with transaction.atomic():
            appointment.status = Appointment.Status.CANCELLED
            appointment.save()

            # Mark unpaid billing as waived
            if hasattr(appointment, 'billing') and appointment.billing.payment_status == AppointmentBilling.PaymentStatus.PENDING:
                appointment.billing.payment_status = AppointmentBilling.PaymentStatus.WAIVED
                appointment.billing.save()

        send_appointment_notification(appointment, 'cancelled')
        messages.success(request, 'Appointment cancelled successfully.')
    else:
        messages.error(request, 'This appointment cannot be cancelled because it is completed or already cancelled.')

    if is_owner:
        return redirect('appointments:my_appointments')
    elif is_doc:
        return redirect('appointments:doctor_appointments')
    return redirect('appointments:all_appointments')


@doctor_required
def doctor_appointments(request):
    """
    Doctor's schedule management dashboard.
    """
    doctor = get_object_or_404(Doctor, user=request.user)
    status_filter = request.GET.get('status', '').strip()
    query = request.GET.get('q', '').strip()

    appointments = Appointment.objects.filter(doctor=doctor).select_related('patient', 'billing')

    if status_filter:
        appointments = appointments.filter(status=status_filter)

    if query:
        appointments = appointments.filter(
            Q(patient__first_name__icontains=query) |
            Q(patient__last_name__icontains=query) |
            Q(patient__username__icontains=query) |
            Q(reason__icontains=query)
        )

    paginator = Paginator(appointments, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'appointments/doctor_appointments.html', {
        'page_obj': page_obj,
        'doctor': doctor,
        'status_choices': Appointment.Status.choices,
        'status_filter': status_filter,
        'query': query,
    })


@doctor_required
def update_appointment_status(request, pk):
    """
    Doctor updates status (accept, complete, cancel) and consult notes.
    """
    doctor = get_object_or_404(Doctor, user=request.user)
    appointment = get_object_or_404(Appointment, pk=pk, doctor=doctor)

    if request.method == 'POST':
        form = AppointmentStatusForm(request.POST, instance=appointment)
        if form.is_valid():
            prev_status = appointment.status
            updated = form.save()

            if updated.status != prev_status:
                if updated.status == Appointment.Status.CONFIRMED:
                    send_appointment_notification(updated, 'confirmed')
                elif updated.status == Appointment.Status.CANCELLED:
                    send_appointment_notification(updated, 'cancelled')

            messages.success(request, f'Appointment status updated to {updated.get_status_display()}.')
            return redirect('appointments:doctor_appointments')
    else:
        form = AppointmentStatusForm(instance=appointment)

    return render(request, 'appointments/update_status.html', {
        'form': form,
        'appointment': appointment,
    })


# ==============================================================================
# PHASE 7: MEDICAL RECORDS & PRESCRIPTIONS VIEWS
# ==============================================================================

@doctor_required
def create_medical_record(request, appointment_pk):
    """
    Doctor creates a formal medical diagnosis/record for a patient consultation.
    """
    doctor = get_object_or_404(Doctor, user=request.user)
    appointment = get_object_or_404(Appointment, pk=appointment_pk, doctor=doctor)

    if request.method == 'POST':
        form = MedicalRecordForm(request.POST, request.FILES)
        if form.is_valid():
            record = form.save(commit=False)
            record.doctor = doctor
            record.patient = appointment.patient
            record.appointment = appointment
            record.save()
            messages.success(request, f"Medical record created for patient {appointment.patient.get_full_name()}.")
            return redirect('appointments:doctor_appointments')
    else:
        form = MedicalRecordForm(initial={'title': f"Consultation for: {appointment.reason[:50]}"})

    return render(request, 'appointments/create_medical_record.html', {
        'form': form,
        'appointment': appointment,
    })


@login_required
def view_medical_record(request, pk):
    """
    Role-protected medical record view.
    Only the owning patient (if released), the authoring doctor, or an admin can access.
    """
    record = get_object_or_404(MedicalRecord, pk=pk)

    is_patient_owner = (record.patient == request.user and record.is_released_to_patient)
    is_doctor_author = (hasattr(request.user, 'doctor_profile') and record.doctor == request.user.doctor_profile)
    is_adm = (request.user.is_superuser or request.user.is_admin_role())

    if not (is_patient_owner or is_doctor_author or is_adm):
        raise PermissionDenied("Access Denied: You are not authorized to view this confidential medical record.")

    return render(request, 'appointments/view_medical_record.html', {
        'record': record,
    })


@doctor_required
def create_prescription(request, appointment_pk):
    """
    Doctor writes an official prescription with prescribed medicine items.
    """
    doctor = get_object_or_404(Doctor, user=request.user)
    appointment = get_object_or_404(Appointment, pk=appointment_pk, doctor=doctor)

    if request.method == 'POST':
        form = PrescriptionForm(request.POST)
        formset = PrescriptionItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                prescription = form.save(commit=False)
                prescription.doctor = doctor
                prescription.patient = appointment.patient
                prescription.appointment = appointment
                prescription.save()

                formset.instance = prescription
                formset.save()

            messages.success(request, f"Prescription issued for patient {appointment.patient.get_full_name()}.")
            return redirect('appointments:doctor_appointments')
    else:
        form = PrescriptionForm(initial={'diagnosis': appointment.reason})
        formset = PrescriptionItemFormSet()

    return render(request, 'appointments/create_prescription.html', {
        'form': form,
        'formset': formset,
        'appointment': appointment,
    })


@login_required
def view_prescription(request, pk):
    """
    Role-protected view for official prescriptions.
    Accessible only to the owning patient, authoring doctor, or admin.
    """
    prescription = get_object_or_404(Prescription, pk=pk)

    is_patient_owner = (prescription.patient == request.user)
    is_doctor_author = (hasattr(request.user, 'doctor_profile') and prescription.doctor == request.user.doctor_profile)
    is_adm = (request.user.is_superuser or request.user.is_admin_role())

    if not (is_patient_owner or is_doctor_author or is_adm):
        raise PermissionDenied("Access Denied: You are not authorized to view this prescription.")

    return render(request, 'appointments/view_prescription.html', {
        'prescription': prescription,
        'items': prescription.items.all(),
    })


@patient_required
def patient_medical_history(request):
    """
    Patient view of all released medical records and prescriptions.
    """
    records = MedicalRecord.objects.filter(
        patient=request.user,
        is_released_to_patient=True
    ).select_related('doctor__user')

    prescriptions = Prescription.objects.filter(
        patient=request.user
    ).select_related('doctor__user').prefetch_related('items')

    return render(request, 'appointments/patient_medical_history.html', {
        'records': records,
        'prescriptions': prescriptions,
    })


# ==============================================================================
# PHASE 8: BILLING & INVOICING VIEWS
# ==============================================================================

@login_required
def view_appointment_invoice(request, pk):
    """
    Role-protected printable and viewable invoice.
    """
    appointment = get_object_or_404(Appointment, pk=pk)
    billing = get_object_or_404(AppointmentBilling, appointment=appointment)

    is_owner = (appointment.patient == request.user)
    is_doc = (hasattr(request.user, 'doctor_profile') and appointment.doctor == request.user.doctor_profile)
    is_adm = (request.user.is_superuser or request.user.is_admin_role())

    if not (is_owner or is_doc or is_adm):
        raise PermissionDenied("Access Denied: You are not authorized to view this invoice.")

    return render(request, 'appointments/invoice_detail.html', {
        'appointment': appointment,
        'billing': billing,
    })


@login_required
@admin_required
def all_appointments_admin(request):
    """
    Admin overview of all hospital appointments with filters.
    """
    status_filter = request.GET.get('status', '').strip()
    query = request.GET.get('q', '').strip()

    appointments = Appointment.objects.select_related('doctor__user', 'doctor__department', 'patient', 'billing').all()

    if status_filter:
        appointments = appointments.filter(status=status_filter)

    if query:
        appointments = appointments.filter(
            Q(patient__first_name__icontains=query) |
            Q(patient__last_name__icontains=query) |
            Q(patient__username__icontains=query) |
            Q(doctor__user__first_name__icontains=query) |
            Q(doctor__user__last_name__icontains=query) |
            Q(reason__icontains=query)
        )

    paginator = Paginator(appointments, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'appointments/all_appointments.html', {
        'page_obj': page_obj,
        'status_choices': Appointment.Status.choices,
        'status_filter': status_filter,
        'query': query,
        'total_appointments': paginator.count,
    })
