import logging
from corepages.email_service import send_appointment_notifications

logger = logging.getLogger(__name__)


def send_appointment_notification(appointment, event_type):
    """
    Backwards-compatible wrapper delegating to central notification service.
    Notifies:
    1. Patient (HTML appointment summary)
    2. Doctor (schedule notification)
    3. Hospital Admin (admin notification for booked, cancelled, rescheduled)
    """
    return send_appointment_notifications(appointment, event_type)
