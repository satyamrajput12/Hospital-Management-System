from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render, redirect
from django.urls import reverse_lazy

from .forms import PatientRegistrationForm, UserProfileForm


class HospitalLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True


class HospitalLogoutView(LogoutView):
    next_page = 'core:home'


def register_patient(request):
    if request.user.is_authenticated:
        return redirect('core:redirect_dashboard')
    if request.method == 'POST':
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful! Welcome to City Care Hospital.')
            return redirect('core:redirect_dashboard')
    else:
        form = PatientRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})


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
