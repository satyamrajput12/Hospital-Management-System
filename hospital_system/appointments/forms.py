import datetime
from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory
from accounts.forms import BootstrapFormMixin
from .models import Appointment, MedicalRecord, Prescription, PrescriptionItem, AppointmentBilling

DAY_CODE_MAP = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']


class AppointmentForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['appointment_date', 'appointment_time', 'reason']
        widgets = {
            'appointment_date': forms.DateInput(attrs={'type': 'date'}),
            'appointment_time': forms.TimeInput(attrs={'type': 'time'}),
            'reason': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Describe your symptoms or reason for visit...'}),
        }

    def __init__(self, *args, **kwargs):
        self.doctor = kwargs.pop('doctor', None)
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()

    def clean_appointment_date(self):
        date = self.cleaned_data['appointment_date']
        if date < datetime.date.today():
            raise ValidationError("Appointment date cannot be in the past.")
        return date

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('appointment_date')
        time = cleaned_data.get('appointment_time')

        if not date or not time:
            return cleaned_data

        doctor = self.doctor or getattr(self.instance, 'doctor', None)
        if not doctor:
            return cleaned_data

        # 1. Check doctor availability on that weekday
        day_code = DAY_CODE_MAP[date.weekday()]
        availabilities = doctor.availabilities.filter(day_of_week=day_code)

        if doctor.availabilities.exists() and not availabilities.exists():
            available_days = ", ".join([d.get_day_of_week_display() for d in doctor.availabilities.all()])
            raise ValidationError({
                'appointment_date': f"Dr. {doctor.user.get_full_name()} is not available on {date.strftime('%A')}s. Available schedule: {available_days}."
            })

        if availabilities.exists():
            slot_valid = any(
                slot.start_time <= time <= slot.end_time
                for slot in availabilities
            )
            if not slot_valid:
                valid_hours = ", ".join([f"{s.start_time.strftime('%I:%M %p')} - {s.end_time.strftime('%I:%M %p')}" for s in availabilities])
                raise ValidationError({
                    'appointment_time': f"Selected time is outside doctor's consultation hours for {date.strftime('%A')} ({valid_hours})."
                })

        # 2. Check for double booking conflicts
        existing_booking = Appointment.objects.filter(
            doctor=doctor,
            appointment_date=date,
            appointment_time=time,
        ).exclude(status=Appointment.Status.CANCELLED)

        if self.instance.pk:
            existing_booking = existing_booking.exclude(pk=self.instance.pk)

        if existing_booking.exists():
            raise ValidationError({
                'appointment_time': "This time slot is already booked for Dr. " + doctor.user.get_full_name() + ". Please choose another time or date."
            })

        return cleaned_data


class AppointmentRescheduleForm(BootstrapFormMixin, forms.Form):
    appointment_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    appointment_time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))
    reschedule_reason = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional reason for rescheduling'}),
        required=False
    )

    def __init__(self, *args, **kwargs):
        self.appointment = kwargs.pop('appointment')
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()
        self.fields['appointment_date'].initial = self.appointment.appointment_date
        self.fields['appointment_time'].initial = self.appointment.appointment_time

    def clean_appointment_date(self):
        date = self.cleaned_data['appointment_date']
        if date < datetime.date.today():
            raise ValidationError("New appointment date cannot be in the past.")
        return date

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('appointment_date')
        time = cleaned_data.get('appointment_time')

        if not date or not time:
            return cleaned_data

        doctor = self.appointment.doctor

        # 1. Check doctor availability
        day_code = DAY_CODE_MAP[date.weekday()]
        availabilities = doctor.availabilities.filter(day_of_week=day_code)
        if doctor.availabilities.exists() and not availabilities.exists():
            raise ValidationError({
                'appointment_date': f"Dr. {doctor.user.get_full_name()} is not available on {date.strftime('%A')}s."
            })

        if availabilities.exists():
            slot_valid = any(slot.start_time <= time <= slot.end_time for slot in availabilities)
            if not slot_valid:
                valid_hours = ", ".join([f"{s.start_time.strftime('%I:%M %p')} - {s.end_time.strftime('%I:%M %p')}" for s in availabilities])
                raise ValidationError({
                    'appointment_time': f"Selected time is outside doctor's consultation hours ({valid_hours})."
                })

        # 2. Check conflict
        existing = Appointment.objects.filter(
            doctor=doctor,
            appointment_date=date,
            appointment_time=time,
        ).exclude(status=Appointment.Status.CANCELLED).exclude(pk=self.appointment.pk)

        if existing.exists():
            raise ValidationError({
                'appointment_time': "This time slot is already booked. Please choose another slot."
            })

        return cleaned_data


class AppointmentStatusForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['status', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Clinical observations, patient history notes...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()


class MedicalRecordForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = MedicalRecord
        fields = ['title', 'diagnosis', 'symptoms', 'treatment_plan', 'notes', 'record_file', 'is_released_to_patient']
        widgets = {
            'diagnosis': forms.Textarea(attrs={'rows': 3}),
            'symptoms': forms.Textarea(attrs={'rows': 2}),
            'treatment_plan': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()


class PrescriptionForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Prescription
        fields = ['diagnosis', 'instructions']
        widgets = {
            'instructions': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Dietary precautions, hydration advice, follow-up schedule...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()


class PrescriptionItemForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = PrescriptionItem
        fields = ['medicine_name', 'dosage', 'frequency', 'duration', 'instructions']
        widgets = {
            'medicine_name': forms.TextInput(attrs={'placeholder': 'e.g. Paracetamol'}),
            'dosage': forms.TextInput(attrs={'placeholder': 'e.g. 500mg'}),
            'frequency': forms.TextInput(attrs={'placeholder': 'e.g. 1-0-1 after meals'}),
            'duration': forms.TextInput(attrs={'placeholder': 'e.g. 5 days'}),
            'instructions': forms.TextInput(attrs={'placeholder': 'e.g. Take with warm water'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()


PrescriptionItemFormSet = inlineformset_factory(
    Prescription,
    PrescriptionItem,
    form=PrescriptionItemForm,
    extra=3,
    can_delete=True
)
