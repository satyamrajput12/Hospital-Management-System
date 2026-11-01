from django.conf import settings
from django.db import models
from departments.models import Department

DAYS_OF_WEEK = [
    ('MON', 'Monday'), ('TUE', 'Tuesday'), ('WED', 'Wednesday'),
    ('THU', 'Thursday'), ('FRI', 'Friday'), ('SAT', 'Saturday'), ('SUN', 'Sunday'),
]


class Doctor(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctor_profile')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, related_name='doctors')
    specialization = models.CharField(max_length=150)
    qualification = models.CharField(max_length=255, blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    consultation_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    bio = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['user__first_name']

    def __str__(self):
        return f"Dr. {self.user.get_full_name() or self.user.username} ({self.specialization})"


class DoctorAvailability(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='availabilities')
    day_of_week = models.CharField(max_length=3, choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_duration_minutes = models.PositiveIntegerField(default=30)

    class Meta:
        ordering = ['doctor', 'day_of_week', 'start_time']
        unique_together = ('doctor', 'day_of_week', 'start_time')

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError({'end_time': 'End time must be after start time.'})

        if self.doctor_id and self.day_of_week and self.start_time and self.end_time:
            overlapping = DoctorAvailability.objects.filter(
                doctor=self.doctor,
                day_of_week=self.day_of_week,
                start_time__lt=self.end_time,
                end_time__gt=self.start_time,
            )
            if self.pk:
                overlapping = overlapping.exclude(pk=self.pk)
            if overlapping.exists():
                raise ValidationError("This availability slot overlaps with an existing slot for this doctor.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.doctor} - {self.get_day_of_week_display()} {self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"
