from django import forms
from django.core.exceptions import ValidationError
from accounts.forms import BootstrapFormMixin
from .models import ProductCategory, Product, Order


class CheckoutForm(BootstrapFormMixin, forms.Form):
    full_name = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={'placeholder': 'Full Name'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'placeholder': 'name@example.com'}))
    phone = forms.CharField(max_length=20, required=True, widget=forms.TextInput(attrs={'placeholder': 'Active phone for delivery updates'}))
    shipping_address = forms.CharField(max_length=255, required=True, widget=forms.TextInput(attrs={'placeholder': 'Flat/House no, Street, Landmark'}))
    city = forms.CharField(max_length=100, initial='New York', required=True, widget=forms.TextInput(attrs={'placeholder': 'City'}))
    postal_code = forms.CharField(max_length=20, required=True, widget=forms.TextInput(attrs={'placeholder': 'Postal/Zip Code'}))
    payment_method = forms.ChoiceField(
        choices=Order.PaymentMethod.choices,
        initial=Order.PaymentMethod.COD,
        widget=forms.RadioSelect
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional delivery notes (e.g. Ring bell, leave with security)'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()
        # Radio buttons shouldn't have form-control class
        if 'payment_method' in self.fields:
            self.fields['payment_method'].widget.attrs['class'] = 'form-check-input'


class ProductForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category', 'description', 'price', 'discount_percent',
                  'stock', 'image', 'rating', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price <= 0:
            raise ValidationError("Price must be greater than zero.")
        return price

    def clean_stock(self):
        stock = self.cleaned_data.get('stock')
        if stock is not None and stock < 0:
            raise ValidationError("Stock cannot be negative.")
        return stock


class ProductCategoryForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ProductCategory
        fields = ['name', 'description', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()


class OrderStatusUpdateForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status', 'payment_status', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()
