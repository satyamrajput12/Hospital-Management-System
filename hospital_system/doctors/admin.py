from django.contrib import admin
from .models import Doctor, DoctorAvailability


class AvailabilityInline(admin.TabularInline):
    model = DoctorAvailability
    extra = 1


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'department', 'experience_years', 'consultation_fee', 'is_active')
    list_filter = ('department', 'is_active')
    search_fields = ('user__first_name', 'user__last_name', 'specialization')
    inlines = [AvailabilityInline]


@admin.register(DoctorAvailability)
class DoctorAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'day_of_week', 'start_time', 'end_time', 'slot_duration_minutes')
    list_filter = ('day_of_week', 'doctor')
