from django.conf import settings
from django.db import models
from doctors.models import Doctor


class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='appointments')
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    reason = models.TextField(help_text="Briefly describe the reason for your visit")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    notes = models.TextField(blank=True, help_text="Doctor's notes after consultation")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-appointment_date', '-appointment_time']
        constraints = [
            models.UniqueConstraint(
                fields=['doctor', 'appointment_date', 'appointment_time'],
                condition=~models.Q(status='CANCELLED'),
                name='unique_active_doctor_appointment'
            )
        ]

    def __str__(self):
        return f"{self.patient} with {self.doctor} on {self.appointment_date} {self.appointment_time}"

    def can_cancel(self):
        return self.status in (self.Status.PENDING, self.Status.CONFIRMED)

    def can_reschedule(self):
        return self.status in (self.Status.PENDING, self.Status.CONFIRMED)


class MedicalRecord(models.Model):
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='medical_records')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='medical_records')
    appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name='medical_records')
    title = models.CharField(max_length=200, help_text="Summary or title of the medical record")
    diagnosis = models.TextField()
    symptoms = models.TextField(blank=True)
    treatment_plan = models.TextField(blank=True)
    notes = models.TextField(blank=True, help_text="Clinical observations and advice")
    record_file = models.FileField(upload_to='medical_records/', null=True, blank=True, help_text="Supporting lab report or document")
    is_released_to_patient = models.BooleanField(default=True, help_text="Controls if the patient can view this record")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Record for {self.patient}: {self.title} (Dr. {self.doctor.user.last_name})"


class Prescription(models.Model):
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='prescriptions')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='prescriptions')
    appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name='prescriptions')
    diagnosis = models.CharField(max_length=255)
    instructions = models.TextField(blank=True, help_text="General instructions, diet, and lifestyle recommendations")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Prescription #{self.pk} for {self.patient} by Dr. {self.doctor.user.last_name}"


class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')
    medicine_name = models.CharField(max_length=150)
    dosage = models.CharField(max_length=100, help_text="e.g. 500mg, 1 tablet")
    frequency = models.CharField(max_length=100, help_text="e.g. Twice daily after meals")
    duration = models.CharField(max_length=100, help_text="e.g. 5 days")
    instructions = models.CharField(max_length=255, blank=True, help_text="e.g. Take with warm water")

    def __str__(self):
        return f"{self.medicine_name} - {self.dosage} ({self.frequency})"


class AppointmentBilling(models.Model):
    class PaymentStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PAID = 'PAID', 'Paid'
        WAIVED = 'WAIVED', 'Waived'

    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='billing')
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='appointment_bills')
    invoice_number = models.CharField(max_length=50, unique=True)
    consultation_fee = models.DecimalField(max_digits=8, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=8, decimal_places=2)
    payment_status = models.CharField(max_length=15, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    payment_method = models.CharField(max_length=60, default='Hospital Front Desk / Cash')
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.patient} (₹{self.total_amount})"
