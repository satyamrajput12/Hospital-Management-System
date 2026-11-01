from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def patient_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_patient_role():
            return view_func(request, *args, **kwargs)
        messages.error(request, "This action is only accessible to patient accounts.")
        return redirect('corepages:redirect_dashboard')
    return _wrapped_view


def doctor_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_doctor_role():
            return view_func(request, *args, **kwargs)
        messages.error(request, "This action is restricted to licensed doctor accounts.")
        return redirect('corepages:redirect_dashboard')
    return _wrapped_view


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_superuser or request.user.is_admin_role():
            return view_func(request, *args, **kwargs)
        messages.error(request, "Access denied. Administrator privileges required.")
        return redirect('corepages:redirect_dashboard')
    return _wrapped_view


def verified_email_required(view_func):
    """
    Blocks unverified accounts from performing sensitive operations
    (booking appointments, ordering pharmacy items, etc.) until verified.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if getattr(request.user, 'is_email_verified', False):
            return view_func(request, *args, **kwargs)
        messages.warning(
            request,
            "Please verify your email address to access this feature. "
            "Check your inbox or request a new verification link from your dashboard."
        )
        return redirect('core:redirect_dashboard')
    return _wrapped_view
