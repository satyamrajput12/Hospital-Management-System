import logging
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_order_confirmation_email(order):
    """
    Sends order receipt email with item breakdown.
    """
    items_text = "\n".join([
        f"- {item.product_name} x {item.quantity} = ₹{item.subtotal}"
        for item in order.items.all()
    ])

    subject = f"Order Placed Successfully — Medicare Pharmacy (#{order.order_number})"
    message = (
        f"Dear {order.full_name},\n\n"
        f"Thank you for ordering with Medicare Doorstep Pharmacy.\n\n"
        f"Order Number: #{order.order_number}\n"
        f"Payment Method: {order.get_payment_method_display()}\n"
        f"Payment Status: {order.get_payment_status_display()}\n"
        f"Delivery Address: {order.shipping_address}, {order.city} - {order.postal_code}\n\n"
        f"Items Ordered:\n{items_text}\n\n"
        f"Total Amount: ₹{order.total_amount}\n\n"
        f"We will notify you once your package is dispatched.\n\n"
        f"Warm regards,\nMedicare Healthcare Team"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.email],
            fail_silently=False,
        )
    except Exception as e:
        logger.warning(f"Could not send order confirmation email to {order.email}: {e}")
