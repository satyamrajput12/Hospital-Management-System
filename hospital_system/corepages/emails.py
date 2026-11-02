import logging
from .email_service import (
    send_pharmacy_order_confirmation,
    send_pharmacy_status_update
)

logger = logging.getLogger(__name__)


def send_order_confirmation_email(order):
    """
    Backwards-compatible wrapper delegating to central notification service.
    Notifies:
    1. Patient (HTML order receipt)
    2. Hospital Admin (admin new order alert)
    """
    return send_pharmacy_order_confirmation(order)


def send_order_status_update_email(order, old_status=None):
    """
    Backwards-compatible wrapper delegating to central notification service.
    Notifies:
    1. Patient (HTML status update)
    2. Hospital Admin (if status is CANCELLED)
    """
    return send_pharmacy_status_update(order, old_status=old_status)
