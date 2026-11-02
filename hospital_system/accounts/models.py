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
    is_email_verified = models.BooleanField(default=True, help_text="Designates whether this user has verified their email.")

    def is_admin_role(self):
        return self.role == self.Role.ADMIN

    def is_doctor_role(self):
        return self.role == self.Role.DOCTOR

    def is_patient_role(self):
        return self.role == self.Role.PATIENT

    def get_avatar_url(self):
        """Returns the user/doctor profile picture URL or a fallback static image."""
        import os
        from django.conf import settings
        from django.templatetags.static import static

        static_map = {
            'drsharma': 'images/doc_1.jpg',
            'drkhan': 'images/doc_2.jpg',
            'drrao': 'images/doc_3.jpg',
            'drgupta': 'images/doc_4.jpg',
            'drpatel': 'images/doc_5.jpg',
            'drmehta': 'images/doc_6.jpg',
        }
        # For seed doctors, prioritize clean, high-res static images
        if self.username in static_map:
            return static(static_map[self.username])

        if self.profile_picture:
            try:
                # Check if the file actually exists on disk before serving media URL
                full_path = os.path.join(settings.MEDIA_ROOT, self.profile_picture.name)
                if os.path.exists(full_path):
                    return self.profile_picture.url
            except Exception:
                pass

        if self.role == self.Role.DOCTOR:
            return static('images/doc_1.jpg')
        return static('images/doc_character.png')

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"
