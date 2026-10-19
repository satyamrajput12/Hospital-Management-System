from django.urls import path
from . import views

app_name = 'appointments'

urlpatterns = [
    path('book/<int:doctor_pk>/', views.book_appointment, name='book'),
    path('my/', views.my_appointments, name='my_appointments'),
    path('<int:pk>/cancel/', views.cancel_appointment, name='cancel'),
    path('doctor/', views.doctor_appointments, name='doctor_appointments'),
    path('doctor/<int:pk>/update/', views.update_appointment_status, name='update_status'),
    path('admin/all/', views.all_appointments_admin, name='all_appointments'),
]
