from django import forms
from django.core.exceptions import ValidationError
from accounts.forms import BootstrapFormMixin
from accounts.models import User
from .models import Doctor, DoctorAvailability


class DoctorProfileForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Doctor
        fields = ['department', 'specialization', 'qualification',
                  'experience_years', 'consultation_fee', 'bio']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Share your clinical background and medical philosophy...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()

    def clean_experience_years(self):
        exp = self.cleaned_data.get('experience_years')
        if exp is not None and exp < 0:
            raise ValidationError("Years of experience cannot be negative.")
        return exp

    def clean_consultation_fee(self):
        fee = self.cleaned_data.get('consultation_fee')
        if fee is not None and fee < 0:
            raise ValidationError("Consultation fee cannot be negative.")
        return fee


class DoctorSelfProfileForm(BootstrapFormMixin, forms.ModelForm):
    """
    Used by a logged-in doctor to edit their own profile and contact information.
    """
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    phone = forms.CharField(max_length=20, required=False)
    address = forms.CharField(max_length=255, required=False)
    profile_picture = forms.ImageField(required=False)

    class Meta:
        model = Doctor
        fields = ['specialization', 'qualification', 'experience_years', 'consultation_fee', 'bio']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['phone'].initial = self.instance.user.phone
            self.fields['address'].initial = self.instance.user.address
            self.fields['profile_picture'].initial = self.instance.user.profile_picture

    def clean_experience_years(self):
        exp = self.cleaned_data.get('experience_years')
        if exp is not None and exp < 0:
            raise ValidationError("Years of experience cannot be negative.")
        return exp

    def clean_consultation_fee(self):
        fee = self.cleaned_data.get('consultation_fee')
        if fee is not None and fee < 0:
            raise ValidationError("Consultation fee cannot be negative.")
        return fee

    def save(self, commit=True):
        doctor = super().save(commit=False)
        user = doctor.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.phone = self.cleaned_data.get('phone', '')
        user.address = self.cleaned_data.get('address', '')
        if self.cleaned_data.get('profile_picture'):
            user.profile_picture = self.cleaned_data['profile_picture']
        if commit:
            user.save()
            doctor.save()
        return doctor


class DoctorAvailabilityForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = DoctorAvailability
        fields = ['day_of_week', 'start_time', 'end_time', 'slot_duration_minutes']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        self.doctor = kwargs.pop('doctor', None)
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_time')
        end = cleaned_data.get('end_time')
        day = cleaned_data.get('day_of_week')

        if start and end and start >= end:
            raise ValidationError({'end_time': "End time must be later than start time."})

        # Check overlapping slots for this doctor
        doctor = self.doctor or getattr(self.instance, 'doctor', None)
        if doctor and day and start and end:
            overlaps = DoctorAvailability.objects.filter(
                doctor=doctor,
                day_of_week=day,
                start_time__lt=end,
                end_time__gt=start
            )
            if self.instance.pk:
                overlaps = overlaps.exclude(pk=self.instance.pk)
            if overlaps.exists():
                raise ValidationError("This schedule overlaps with an existing availability slot on the same day.")

        return cleaned_data
