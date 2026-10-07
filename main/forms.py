from django import forms

from .models import Order


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ("customer_name", "email", "phone", "shipping_address")
        widgets = {
            "shipping_address": forms.Textarea(attrs={"rows": 3}),
        }