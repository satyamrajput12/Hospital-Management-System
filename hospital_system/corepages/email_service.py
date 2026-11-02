import logging
from decimal import Decimal
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def get_admin_recipient():
    """
    Returns the configured hospital admin email address.
    Falls back to first active admin in database or settings.DEFAULT_FROM_EMAIL.
    """
    admin_email = getattr(settings, 'HOSPITAL_ADMIN_EMAIL', '').strip()
    if admin_email and admin_email != 'admin@medicare.local':
        return admin_email

    # Check for active administrator user in the database
    try:
        from accounts.models import User
        admin_user = User.objects.filter(role=User.Role.ADMIN, is_active=True).exclude(email='').first()
        if admin_user and admin_user.email:
            return admin_user.email
    except Exception:
        pass

    return getattr(settings, 'EMAIL_HOST_USER', '') or admin_email or 'admin@medicare.local'


def send_safe_email(subject, text_content, recipient_list, html_content=None):
    """
    Reusable email dispatch utility.
    Safely dispatches multi-part HTML/text email without raising exceptions
    to prevent rolling back caller database transactions.
    """
    valid_recipients = [r.strip() for r in recipient_list if r and r.strip()]
    if not valid_recipients:
        logger.warning(f"No valid recipients provided for email: '{subject}'")
        return False

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'Medicare Hospital <noreply@medicare.local>')

    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=valid_recipients,
        )
        if html_content:
            msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)
        logger.info(f"Email successfully delivered: '{subject}' -> {valid_recipients}")
        return True
    except Exception as e:
        logger.error(f"Failed to deliver email '{subject}' to {valid_recipients}: {e}")
        return False


# ==============================================================================
# APPOINTMENT NOTIFICATIONS
# ==============================================================================

def send_appointment_notifications(appointment, event_type):
    """
    Dispatches appointment notifications:
    1. Patient confirmation / status update (HTML summary)
    2. Assigned Doctor alert (plain text schedule update)
    3. Hospital Admin alert (HTML admin summary)
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
    title_map = {
        'booked': "Appointment Booked",
        'confirmed': "Appointment Confirmed",
        'cancelled': "Appointment Cancelled",
        'rescheduled': "Appointment Rescheduled",
    }

    event_title = title_map.get(event_type, "Appointment Update")
    patient_subject = subject_map.get(event_type, f"Appointment Update — Medicare (#{appointment.pk})")

    # 1. Patient Notification (HTML + Text)
    if patient.email:
        patient_context = {
            'appointment': appointment,
            'doctor': doctor,
            'patient': patient,
            'date_str': date_str,
            'time_str': time_str,
            'event_type': event_type,
            'event_title': event_title,
        }
        try:
            patient_html = render_to_string('appointments/emails/appointment_summary.html', patient_context)
        except Exception as e:
            logger.error(f"Error rendering patient appointment template: {e}")
            patient_html = None

        patient_text = (
            f"Dear {patient.get_full_name() or patient.username},\n\n"
            f"This is an update regarding your appointment with Dr. {doctor.user.get_full_name()} ({doctor.specialization}).\n\n"
            f"-----------------------------------------\n"
            f"APPOINTMENT SUMMARY: #{appointment.pk}\n"
            f"-----------------------------------------\n"
            f"Doctor: Dr. {doctor.user.get_full_name()} ({doctor.specialization} - {doctor.department.name if doctor.department else 'General OPD'})\n"
            f"Status: {appointment.get_status_display()}\n"
            f"Date: {date_str}\n"
            f"Time: {time_str}\n"
            f"Reason for Visit: {appointment.reason or 'General Health Checkup'}\n"
            f"Consultation Fee: ₹{doctor.consultation_fee}\n"
            f"Hospital Location: Central Wing & OPD Reception, Room {doctor.pk + 200}\n\n"
            f"Visit Guidelines:\n"
            f"- Please arrive 15 minutes before your slot.\n"
            f"- Carry previous medical records and valid photo ID.\n\n"
            f"Warm regards,\nMedicare Healthcare Management\n24/7 Helpline: 108 / 102"
        )
        send_safe_email(patient_subject, patient_text, [patient.email], patient_html)

    # 2. Doctor Schedule Notification
    if event_type in ('booked', 'cancelled', 'rescheduled') and doctor.user.email:
        doc_subject = f"Patient Schedule Alert: {event_title} — {patient.get_full_name()} (#{appointment.pk})"
        doc_message = (
            f"Dear Dr. {doctor.user.get_full_name()},\n\n"
            f"An appointment with patient {patient.get_full_name() or patient.username} has been {event_type}.\n\n"
            f"Appointment ID: #{appointment.pk}\n"
            f"Date: {date_str}\n"
            f"Time: {time_str}\n"
            f"Reason: {appointment.reason or 'N/A'}\n\n"
            f"Please review your schedule on the Medicare Doctor Portal."
        )
        send_safe_email(doc_subject, doc_message, [doctor.user.email])

    # 3. Hospital Admin Notification (For Bookings, Cancellations & Reschedules)
    admin_recipient = get_admin_recipient()
    if admin_recipient and event_type in ('booked', 'cancelled', 'rescheduled'):
        admin_subject = f"[Admin Alert: {event_title}] #{appointment.pk} — {patient.get_full_name()} with Dr. {doctor.user.get_full_name()}"
        admin_context = {
            'appointment': appointment,
            'doctor': doctor,
            'patient': patient,
            'date_str': date_str,
            'time_str': time_str,
            'event_type': event_type,
            'event_title': event_title,
        }
        try:
            admin_html = render_to_string('appointments/emails/admin_appointment_alert.html', admin_context)
        except Exception as e:
            logger.error(f"Error rendering admin appointment alert template: {e}")
            admin_html = None

        admin_text = (
            f"MEDICARE HOSPITAL - ADMIN APPOINTMENT ALERT\n"
            f"Event: {event_title}\n"
            f"Appointment ID: #{appointment.pk}\n"
            f"Patient: {patient.get_full_name() or patient.username} ({patient.email or 'No email'})\n"
            f"Doctor: Dr. {doctor.user.get_full_name()} ({doctor.department.name if doctor.department else 'General'})\n"
            f"Date & Time: {date_str} at {time_str}\n"
            f"Status: {appointment.get_status_display()}\n"
            f"Consultation Fee: ₹{doctor.consultation_fee}\n"
        )
        send_safe_email(admin_subject, admin_text, [admin_recipient], admin_html)


# ==============================================================================
# PHARMACY ORDER NOTIFICATIONS
# ==============================================================================

def send_pharmacy_order_confirmation(order):
    """
    Dispatches order placement notifications:
    1. Patient confirmation with item breakdown (HTML receipt)
    2. Hospital Admin alert with item breakdown (HTML dispatch notification)
    """
    items = list(order.items.all())
    subtotal = sum((item.subtotal for item in items), Decimal('0.00'))
    shipping = order.total_amount - subtotal
    if shipping < Decimal('0.00'):
        shipping = Decimal('0.00')

    # Plain-text items breakdown
    items_text = "\n".join([
        f"- {item.product_name} x {item.quantity} = ₹{item.subtotal}"
        for item in items
    ])

    # 1. Patient Order Confirmation Email
    if order.email:
        patient_subject = f"Order Placed Successfully — Medicare Pharmacy (#{order.order_number})"
        patient_context = {
            'order': order,
            'items': items,
            'subtotal': subtotal,
            'shipping': shipping,
        }
        try:
            patient_html = render_to_string('corepages/emails/order_summary.html', patient_context)
        except Exception as e:
            logger.error(f"Error rendering patient order summary template: {e}")
            patient_html = None

        patient_text = (
            f"Dear {order.full_name},\n\n"
            f"Thank you for ordering with Medicare Doorstep Pharmacy.\n\n"
            f"-----------------------------------------\n"
            f"ORDER SUMMARY: #{order.order_number}\n"
            f"-----------------------------------------\n"
            f"Order Date: {order.created_at.strftime('%B %d, %Y, %I:%M %p')}\n"
            f"Payment Method: {order.get_payment_method_display()}\n"
            f"Payment Status: {order.get_payment_status_display()}\n"
            f"Delivery Address: {order.shipping_address}, {order.city} - {order.postal_code}\n"
            f"Phone: {order.phone}\n\n"
            f"ITEMS ORDERED:\n{items_text}\n\n"
            f"Medicines Subtotal: ₹{subtotal}\n"
            f"Delivery Fee: {'FREE' if shipping == 0 else f'₹{shipping}'}\n"
            f"Total Amount: ₹{order.total_amount}\n\n"
            f"Warm regards,\nMedicare Healthcare Team\n24/7 Helpline: 108 / 102"
        )
        send_safe_email(patient_subject, patient_text, [order.email], patient_html)

    # 2. Hospital Admin Order Alert
    admin_recipient = get_admin_recipient()
    if admin_recipient:
        admin_subject = f"[Admin Alert: New Pharmacy Order] #{order.order_number} — ₹{order.total_amount}"
        admin_context = {
            'order': order,
            'items': items,
            'subtotal': subtotal,
            'shipping': shipping,
        }
        try:
            admin_html = render_to_string('corepages/emails/admin_order_alert.html', admin_context)
        except Exception as e:
            logger.error(f"Error rendering admin order alert template: {e}")
            admin_html = None

        admin_text = (
            f"MEDICARE PHARMACY - NEW ORDER DISPATCH ALERT\n"
            f"Order Number: #{order.order_number}\n"
            f"Customer: {order.full_name} ({order.email}, {order.phone})\n"
            f"Delivery Address: {order.shipping_address}, {order.city} - {order.postal_code}\n"
            f"Payment Method: {order.get_payment_method_display()} ({order.get_payment_status_display()})\n\n"
            f"ITEMS:\n{items_text}\n\n"
            f"Subtotal: ₹{subtotal} | Shipping: ₹{shipping} | Grand Total: ₹{order.total_amount}\n"
        )
        send_safe_email(admin_subject, admin_text, [admin_recipient], admin_html)


def send_pharmacy_status_update(order, old_status=None):
    """
    Dispatches order status update notifications:
    1. Patient notification (HTML status pill & timeline)
    2. If status is CANCELLED, also alerts the Hospital Admin
    """
    if not order.email:
        return

    subject = f"Order #{order.order_number} Update: Now {order.get_status_display()} — Medicare Pharmacy"
    context = {
        'order': order,
        'old_status': old_status,
    }
    try:
        html_content = render_to_string('corepages/emails/order_status_update.html', context)
    except Exception as e:
        logger.error(f"Error rendering order status update template: {e}")
        html_content = None

    text_content = (
        f"Dear {order.full_name},\n\n"
        f"The status of your Medicare Pharmacy order #{order.order_number} has been updated:\n\n"
        f"New Status: {order.get_status_display()}\n"
        f"{f'Previous Status: {dict(order.Status.choices).get(old_status, old_status)}' if old_status else ''}\n"
        f"Total Amount: ₹{order.total_amount}\n"
        f"Delivery Address: {order.shipping_address}, {order.city}\n\n"
        f"You can view complete order tracking in your patient dashboard.\n\n"
        f"Warm regards,\nMedicare Healthcare Team"
    )

    send_safe_email(subject, text_content, [order.email], html_content)

    # If the order was cancelled, also alert the admin
    if order.status == order.Status.CANCELLED:
        admin_recipient = get_admin_recipient()
        if admin_recipient:
            admin_subject = f"[Admin Alert: Order Cancelled] #{order.order_number} — {order.full_name}"
            admin_text = (
                f"Pharmacy Order #{order.order_number} was CANCELLED.\n"
                f"Customer: {order.full_name} ({order.email})\n"
                f"Total: ₹{order.total_amount}\n"
                f"Stock has been restored."
            )
            send_safe_email(admin_subject, admin_text, [admin_recipient])

