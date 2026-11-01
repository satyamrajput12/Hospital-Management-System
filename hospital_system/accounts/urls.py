from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('login/', views.HospitalLoginView.as_view(), name='login'),
    path('logout/', views.HospitalLogoutView.as_view(), name='logout'),
    path('register/', views.register_patient, name='register'),
    path('profile/', views.profile_view, name='profile'),

    # Email Verification
    path('verify-email/<uidb64>/<token>/', views.verify_email, name='verify_email'),
    path('resend-verification/', views.resend_verification_email, name='resend_verification'),
    path('resend-verification-email/', views.resend_verification_email, name='resend_verification_email'),

    # Password Reset
    path('password-reset/', views.HospitalPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', views.HospitalPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', views.HospitalPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset/complete/', views.HospitalPasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # Password Change (Authenticated)
    path('password-change/', views.HospitalPasswordChangeView.as_view(), name='password_change'),
    path('password-change/done/', views.HospitalPasswordChangeDoneView.as_view(), name='password_change_done'),

    # Admin User Management
    path('admin/patients/', views.admin_patient_list, name='admin_patient_list'),
    path('admin/users/<int:pk>/toggle/', views.toggle_user_active, name='toggle_user_active'),
]
