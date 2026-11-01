from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Emoji or short icon label, e.g. 'heart'")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class LabTest(models.Model):
    name = models.CharField(max_length=150, unique=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='lab_tests')
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    discount_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    preparation_instructions = models.TextField(blank=True, help_text="e.g. 10-12 hours fasting required")
    duration = models.CharField(max_length=100, default='24-48 hours', help_text="Report turnaround time")
    sample_type = models.CharField(max_length=100, default='Blood / Urine', help_text="e.g. Blood, Urine, Imaging")
    image = models.ImageField(upload_to='lab_tests/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def effective_price(self):
        if self.discount_price and self.discount_price > 0 and self.discount_price < self.price:
            return self.discount_price
        return self.price

    def discount_percentage(self):
        if self.discount_price and self.price and self.discount_price < self.price:
            diff = self.price - self.discount_price
            return int((diff / self.price) * 100)
        return 0


class LabBooking(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    class CollectionType(models.TextChoices):
        HOME = 'HOME', 'Home Sample Collection'
        HOSPITAL = 'HOSPITAL', 'Hospital Walk-in'

    patient = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='lab_bookings'
    )
    test = models.ForeignKey(LabTest, on_delete=models.CASCADE, related_name='bookings')
    appointment_date = models.DateField()
    time_slot = models.CharField(
        max_length=60,
        default='08:00 AM - 10:00 AM',
        help_text="Selected appointment window"
    )
    collection_type = models.CharField(
        max_length=10,
        choices=CollectionType.choices,
        default=CollectionType.HOME
    )
    collection_address = models.CharField(max_length=255, blank=True)
    patient_phone = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    price_charged = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-appointment_date', '-created_at']

    def __str__(self):
        return f"{self.patient} - {self.test} on {self.appointment_date} ({self.get_status_display()})"

    def can_cancel(self):
        return self.status in (self.Status.PENDING, self.Status.CONFIRMED)
