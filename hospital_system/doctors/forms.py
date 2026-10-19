from django import forms
from accounts.forms import BootstrapFormMixin
from .models import Doctor, DoctorAvailability


class DoctorProfileForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Doctor
        fields = ['department', 'specialization', 'qualification',
                  'experience_years', 'consultation_fee', 'bio']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()


class DoctorAvailabilityForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = DoctorAvailability
        fields = ['day_of_week', 'start_time', 'end_time', 'slot_duration_minutes']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()
