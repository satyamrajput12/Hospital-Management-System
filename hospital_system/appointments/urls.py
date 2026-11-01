from django.urls import path
from . import views

app_name = 'appointments'

urlpatterns = [
    # Booking & Patient Views
    path('book/<int:doctor_pk>/', views.book_appointment, name='book'),
    path('book/<int:doctor_pk>/', views.book_appointment, name='book_appointment'),
    path('my/', views.my_appointments, name='my_appointments'),
    path('<int:pk>/reschedule/', views.reschedule_appointment, name='reschedule'),
    path('<int:pk>/reschedule/', views.reschedule_appointment, name='reschedule_appointment'),
    path('<int:pk>/cancel/', views.cancel_appointment, name='cancel'),
    path('<int:pk>/cancel/', views.cancel_appointment, name='cancel_appointment'),

    # Doctor Workflow
    path('doctor/', views.doctor_appointments, name='doctor_appointments'),
    path('doctor/<int:pk>/update/', views.update_appointment_status, name='update_status'),

    # Medical Records & Prescriptions
    path('doctor/<int:appointment_pk>/record/create/', views.create_medical_record, name='create_medical_record'),
    path('record/<int:pk>/', views.view_medical_record, name='view_medical_record'),
    path('doctor/<int:appointment_pk>/prescription/create/', views.create_prescription, name='create_prescription'),
    path('prescription/<int:pk>/', views.view_prescription, name='view_prescription'),
    path('history/', views.patient_medical_history, name='patient_medical_history'),

    # Invoices & Billing
    path('invoice/<int:pk>/', views.view_appointment_invoice, name='invoice_detail'),
    path('invoice/<int:pk>/', views.view_appointment_invoice, name='view_invoice'),

    # Admin All Appointments
    path('admin/all/', views.all_appointments_admin, name='all_appointments'),
]
