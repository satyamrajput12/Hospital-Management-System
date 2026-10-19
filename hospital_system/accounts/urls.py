from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.HospitalLoginView.as_view(), name='login'),
    path('logout/', views.HospitalLogoutView.as_view(), name='logout'),
    path('register/', views.register_patient, name='register'),
    path('profile/', views.profile_view, name='profile'),
]
