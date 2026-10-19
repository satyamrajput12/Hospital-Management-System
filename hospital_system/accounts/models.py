from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        DOCTOR = 'DOCTOR', 'Doctor'
        PATIENT = 'PATIENT', 'Patient'

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.PATIENT)
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)

    def is_admin_role(self):
        return self.role == self.Role.ADMIN

    def is_doctor_role(self):
        return self.role == self.Role.DOCTOR

    def is_patient_role(self):
        return self.role == self.Role.PATIENT

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"
