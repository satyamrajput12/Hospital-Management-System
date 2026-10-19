from django.urls import path
from . import views

app_name = 'doctors'

urlpatterns = [
    path('', views.doctor_list, name='list'),
    path('<int:pk>/', views.doctor_detail, name='detail'),
    path('manage/add/', views.add_doctor, name='add_doctor'),
    path('manage/', views.manage_doctor_list, name='manage_list'),
    path('manage/<int:pk>/toggle/', views.toggle_doctor_active, name='toggle_active'),
    path('availability/', views.doctor_availability_manage, name='availability_manage'),
    path('availability/<int:pk>/delete/', views.delete_availability, name='delete_availability'),
]
