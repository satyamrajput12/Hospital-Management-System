from django.urls import path
from . import views

app_name = 'doctors'

urlpatterns = [
    path('', views.doctor_list, name='list'),
    path('', views.doctor_list, name='doctor_list'),
    path('<int:pk>/', views.doctor_detail, name='detail'),
    path('<int:pk>/', views.doctor_detail, name='doctor_detail'),
    path('profile/edit/', views.doctor_profile_edit, name='profile_edit'),
    path('profile/edit/', views.doctor_profile_edit, name='doctor_profile_edit'),
    path('manage/', views.manage_doctor_list, name='manage_list'),
    path('manage/', views.manage_doctor_list, name='manage_doctors'),
    path('manage/add/', views.add_doctor, name='add_doctor'),
    path('manage/<int:pk>/edit/', views.admin_edit_doctor, name='admin_edit_doctor'),
    path('manage/<int:pk>/toggle/', views.toggle_doctor_active, name='toggle_active'),
    path('manage/<int:pk>/toggle/', views.toggle_doctor_active, name='toggle_doctor_active'),
    path('availability/', views.doctor_availability_manage, name='availability_manage'),
    path('availability/<int:pk>/delete/', views.delete_availability, name='delete_availability'),
]
