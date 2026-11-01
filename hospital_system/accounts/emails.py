import logging
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .tokens import account_activation_token

logger = logging.getLogger(__name__)


def send_verification_email(request, user):
    """
    Sends an email verification link to the given user.
    """
    try:
        token = account_activation_token.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Build absolute URL using request
        scheme = 'https' if request.is_secure() else 'http'
        host = request.get_host()
        verify_url = f"{scheme}://{host}/accounts/verify-email/{uid}/{token}/"

        subject = "Verify your Medicare Hospital Account"
        message = (
            f"Dear {user.get_full_name() or user.username},\n\n"
            f"Thank you for registering with Medicare Healthcare Management System.\n\n"
            f"Please click the link below to verify your email address:\n"
            f"{verify_url}\n\n"
            f"If you did not register for a Medicare account, please ignore this email.\n\n"
            f"Best regards,\nMedicare Healthcare Team"
        )
        html_message = render_to_string('accounts/emails/verify_email.html', {
            'user': user,
            'verify_url': verify_url,
        })

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send verification email to {user.email}: {e}")
        return False
