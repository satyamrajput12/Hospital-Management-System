from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User


class EmailOrUsernameAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Username or E-mail",
        widget=forms.TextInput(attrs={
            'class': 'form-control mc-login-input',
            'placeholder': 'Aya_99@gmail.com',
            'autofocus': True,
            'id': 'id_username',
        })
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control mc-login-input',
            'placeholder': '••••••••',
            'id': 'id_password',
        })
    )

    error_messages = {
        'invalid_login': "The username or password is incorrect",
        'inactive': "This account is inactive.",
    }

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username is not None and password:
            # If an email is provided, resolve to username
            if '@' in username:
                user_match = User.objects.filter(email__iexact=username.strip()).first()
                if user_match:
                    username = user_match.username

            self.user_cache = authenticate(self.request, username=username, password=password)
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data


class BootstrapFormMixin:
    def apply_bootstrap(self):
        for field in self.fields.values():
            existing = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (existing + ' form-control').strip()


class PatientRegistrationForm(BootstrapFormMixin, UserCreationForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=False)
    address = forms.CharField(max_length=255, required=False)
    date_of_birth = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone',
                  'address', 'date_of_birth', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()
        if 'username' in self.fields:
            self.fields['username'].help_text = ''
        if 'password1' in self.fields:
            self.fields['password1'].help_text = ''
        if 'password2' in self.fields:
            self.fields['password2'].help_text = ''

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.PATIENT
        user.email = self.cleaned_data['email']
        user.phone = self.cleaned_data.get('phone', '')
        user.address = self.cleaned_data.get('address', '')
        user.date_of_birth = self.cleaned_data.get('date_of_birth')
        user.is_email_verified = False
        if commit:
            user.save()
        return user


class DoctorRegistrationForm(BootstrapFormMixin, UserCreationForm):
    """Used by admin to create doctor accounts along with Doctor profile."""
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=False)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.DOCTOR
        user.email = self.cleaned_data['email']
        user.phone = self.cleaned_data.get('phone', '')
        user.is_email_verified = True
        if commit:
            user.save()
        return user


class UserProfileForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'address',
                  'date_of_birth', 'profile_picture']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()
