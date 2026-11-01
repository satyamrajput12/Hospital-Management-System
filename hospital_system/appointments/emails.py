import logging
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_appointment_notification(appointment, event_type):
    """
    Sends transactional emails for appointment events:
    - 'booked': sent to patient and doctor
    - 'confirmed': sent to patient
    - 'cancelled': sent to patient and doctor
    - 'rescheduled': sent to patient and doctor
    """
    patient = appointment.patient
    doctor = appointment.doctor
    date_str = appointment.appointment_date.strftime('%B %d, %Y')
    time_str = appointment.appointment_time.strftime('%I:%M %p')

    subject_map = {
        'booked': f"Appointment Request Submitted — Medicare (#{appointment.pk})",
        'confirmed': f"Appointment Confirmed — Dr. {doctor.user.get_full_name()} (#{appointment.pk})",
        'cancelled': f"Appointment Cancelled — Medicare (#{appointment.pk})",
        'rescheduled': f"Appointment Rescheduled — Medicare (#{appointment.pk})",
    }

    subject = subject_map.get(event_type, f"Appointment Update — Medicare (#{appointment.pk})")

    message = (
        f"Dear {patient.get_full_name() or patient.username},\n\n"
        f"This is an update regarding your appointment with Dr. {doctor.user.get_full_name()} ({doctor.specialization}).\n\n"
        f"Status: {appointment.get_status_display()}\n"
        f"Date: {date_str}\n"
        f"Time: {time_str}\n"
        f"Department: {doctor.department.name if doctor.department else 'General'}\n"
        f"Consultation Fee: ₹{doctor.consultation_fee}\n\n"
        f"You can view complete details, invoices, and prescriptions anytime in your Medicare dashboard.\n\n"
        f"Warm regards,\n"
        f"Medicare Healthcare Management"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[patient.email],
            fail_silently=False,
        )
    except Exception as e:
        logger.warning(f"Could not deliver appointment email to {patient.email}: {e}")

    # Also notify doctor for new bookings or cancellations
    if event_type in ('booked', 'cancelled', 'rescheduled') and doctor.user.email:
        doc_subject = f"Patient Schedule Alert: {event_type.title()} — {patient.get_full_name()} (#{appointment.pk})"
        doc_message = (
            f"Dear Dr. {doctor.user.get_full_name()},\n\n"
            f"An appointment with patient {patient.get_full_name() or patient.username} has been {event_type}.\n\n"
            f"Date: {date_str}\n"
            f"Time: {time_str}\n"
            f"Reason: {appointment.reason}\n\n"
            f"Please review your schedule on the Medicare Doctor Portal."
        )
        try:
            send_mail(
                subject=doc_subject,
                message=doc_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[doctor.user.email],
                fail_silently=False,
            )
        except Exception as e:
            logger.warning(f"Could not deliver appointment alert to doctor {doctor.user.email}: {e}")
