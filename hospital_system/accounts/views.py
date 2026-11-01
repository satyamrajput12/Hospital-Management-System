import time
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
    LoginView, LogoutView,
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView,
    PasswordChangeView, PasswordChangeDoneView
)
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_decode
from django.views.decorators.http import require_POST

from .decorators import admin_required
from .emails import send_verification_email
from .forms import (
    PatientRegistrationForm, UserProfileForm,
    EmailOrUsernameAuthenticationForm
)
from .models import User
from .tokens import account_activation_token


class HospitalLoginView(LoginView):
    form_class = EmailOrUsernameAuthenticationForm
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        redirect_to = self.request.POST.get(
            self.redirect_field_name,
            self.request.GET.get(self.redirect_field_name, '')
        )
        url_is_safe = url_has_allowed_host_and_scheme(
            url=redirect_to,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        )
        if url_is_safe:
            return redirect_to
        return reverse_lazy('core:redirect_dashboard')


class HospitalLogoutView(LogoutView):
    next_page = 'core:home'

    def get(self, request, *args, **kwargs):
        # Support safe GET logout as fallback with confirmation/redirect
        return self.post(request, *args, **kwargs)


def register_patient(request):
    if request.user.is_authenticated:
        return redirect('core:redirect_dashboard')

    if request.method == 'POST':
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            
            # Send verification email
            sent = send_verification_email(request, user)
            if sent:
                messages.success(
                    request,
                    f'Registration successful! A verification email has been sent to {user.email}. '
                    'Please verify your email address to enable appointment booking and orders.'
                )
            else:
                messages.warning(
                    request,
                    'Registration successful, but we could not send the verification email right now. '
                    'You can resend it from your dashboard.'
                )
            return redirect('core:redirect_dashboard')
    else:
        form = PatientRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})


def verify_email(request, uidb64, token):
    """
    Verifies user email using the uidb64 and expiring token.
    """
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_email_verified = True
        user.save()
        messages.success(request, 'Your email has been verified successfully! You now have full access to Medicare services.')
        if request.user.is_authenticated:
            return redirect('core:redirect_dashboard')
        return redirect('accounts:login')
    else:
        messages.error(request, 'The verification link is invalid, already used, or has expired.')
        return render(request, 'accounts/verification_failed.html')


@login_required
@require_POST
def resend_verification_email(request):
    """
    Resends verification email with a 60-second rate-limiting cooldown.
    """
    if request.user.is_email_verified:
        messages.info(request, "Your email is already verified.")
        return redirect('core:redirect_dashboard')

    last_sent = request.session.get('last_verification_sent_time', 0)
    current_time = int(time.time())
    cooldown = 60  # seconds

    if current_time - last_sent < cooldown:
        remaining = cooldown - (current_time - last_sent)
        messages.warning(request, f"Please wait {remaining} seconds before requesting another verification email.")
        return redirect('core:redirect_dashboard')

    sent = send_verification_email(request, request.user)
    if sent:
        request.session['last_verification_sent_time'] = current_time
        messages.success(request, f"A fresh verification email has been sent to {request.user.email}.")
    else:
        messages.error(request, "Could not send verification email at this moment. Please check server settings.")

    return redirect('core:redirect_dashboard')


@login_required
def profile_view(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'accounts/profile.html', {'form': form})


# ==============================================================================
# PASSWORD RESET & CHANGE VIEWS
# ==============================================================================

class HospitalPasswordResetView(PasswordResetView):
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/password_reset_email.html'
    subject_template_name = 'accounts/password_reset_subject.txt'
    success_url = reverse_lazy('accounts:password_reset_done')


class HospitalPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'accounts/password_reset_done.html'


class HospitalPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:password_reset_complete')


class HospitalPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'accounts/password_reset_complete.html'


class HospitalPasswordChangeView(PasswordChangeView):
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('accounts:password_change_done')


class HospitalPasswordChangeDoneView(PasswordChangeDoneView):
    template_name = 'accounts/password_change_done.html'


# ==============================================================================
# ADMIN USER MANAGEMENT VIEWS (PHASE 2)
# ==============================================================================

@login_required
@admin_required
def admin_patient_list(request):
    """
    Allows Admin to view, search, and manage patient accounts.
    """
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    patients = User.objects.filter(role=User.Role.PATIENT).order_by('-date_joined')

    if query:
        patients = patients.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        )

    if status_filter == 'active':
        patients = patients.filter(is_active=True)
    elif status_filter == 'inactive':
        patients = patients.filter(is_active=False)

    paginator = Paginator(patients, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'accounts/admin_patient_list.html', {
        'page_obj': page_obj,
        'query': query,
        'status_filter': status_filter,
        'total_patients': patients.count(),
    })


@login_required
@admin_required
@require_POST
def toggle_user_active(request, pk):
    """
    Safely activate or deactivate user accounts via POST with CSRF.
    Prevents administrators from deactivating their own account.
    """
    user_to_toggle = get_object_or_404(User, pk=pk)

    if user_to_toggle == request.user:
        messages.error(request, "Security protection: You cannot deactivate your own administrative account.")
        return redirect('accounts:admin_patient_list')

    user_to_toggle.is_active = not user_to_toggle.is_active
    user_to_toggle.save()

    status_str = "activated" if user_to_toggle.is_active else "deactivated"
    messages.success(request, f"Account for {user_to_toggle.get_full_name() or user_to_toggle.username} has been {status_str}.")

    next_url = request.POST.get('next')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)

    if user_to_toggle.role == User.Role.DOCTOR:
        return redirect('doctors:manage_list')
    return redirect('accounts:admin_patient_list')
