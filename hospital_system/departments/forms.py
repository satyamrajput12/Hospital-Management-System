import datetime
from django import forms
from django.core.exceptions import ValidationError
from accounts.forms import BootstrapFormMixin
from .models import Department, LabTest, LabBooking


class DepartmentForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'description', 'icon', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'icon': forms.TextInput(attrs={'placeholder': "e.g. 'heart', 'activity', 'brain'"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()


class LabTestForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = LabTest
        fields = ['name', 'department', 'description', 'price', 'discount_price',
                  'preparation_instructions', 'duration', 'sample_type', 'image', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'preparation_instructions': forms.Textarea(attrs={'rows': 2, 'placeholder': 'e.g. 10-12 hours fasting required'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()

    def clean_price(self):
        p = self.cleaned_data.get('price')
        if p is not None and p <= 0:
            raise ValidationError("Price must be greater than zero.")
        return p

    def clean_discount_price(self):
        dp = self.cleaned_data.get('discount_price')
        if dp is not None and dp < 0:
            raise ValidationError("Discount price cannot be negative.")
        return dp


class LabBookingForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = LabBooking
        fields = ['appointment_date', 'time_slot', 'collection_type', 'collection_address', 'patient_phone', 'notes']
        widgets = {
            'appointment_date': forms.DateInput(attrs={'type': 'date'}),
            'collection_address': forms.TextInput(attrs={'placeholder': 'Complete address for home collection'}),
            'patient_phone': forms.TextInput(attrs={'placeholder': 'Phone number for sample collector to call'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Any specific medical instructions or landmarks...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()

    def clean_appointment_date(self):
        date = self.cleaned_data.get('appointment_date')
        if date and date < datetime.date.today():
            raise ValidationError("Lab appointment date cannot be in the past.")
        return date

    def clean(self):
        cleaned_data = super().clean()
        col_type = cleaned_data.get('collection_type')
        address = cleaned_data.get('collection_address')

        if col_type == LabBooking.CollectionType.HOME and not address:
            raise ValidationError({'collection_address': "Home address is required for home sample collection."})

        return cleaned_data


class LabBookingStatusForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = LabBooking
        fields = ['status', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()
