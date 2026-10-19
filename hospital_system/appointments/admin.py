from django.contrib import admin
from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'appointment_date', 'appointment_time', 'status')
    list_filter = ('status', 'appointment_date', 'doctor__department')
    search_fields = ('patient__username', 'patient__first_name', 'doctor__user__first_name')
    date_hierarchy = 'appointment_date'
