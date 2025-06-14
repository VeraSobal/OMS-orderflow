import logging
from datetime import date

from django import forms
from django.core.exceptions import ValidationError

from ..models.orders import (
    Order,
    OrderItem,
)

log = logging.getLogger(__name__)


class OrderModelForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['name', 'order_date', 'supplier', 'comment']
        labels = {
            'name': 'Name',
            'order_date': 'Date',
            'supplier': 'Supplier',
            'comment': 'Comment',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Input order name'}),
            'order_date': forms.DateInput(attrs={'class': 'form-control', 'placeholder': 'Input order date'}),
            'supplier': forms.Select(attrs={'class': 'form-control'}),
            'comment': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Input comment'}),
        }

    def clean_order_date(self):
        order_date = self.cleaned_data.get('order_date')
        if order_date > date.today():
            raise ValidationError("Order date must be past")
        return order_date

    def clean_name(self):
        name = self.cleaned_data.get('name')
        order_id = Order.name_into_id(name)
        try:
            Order.objects.get(id=order_id)
            raise ValidationError("There is order with such name")
        except Order.DoesNotExist:
            return name


class BaseOrderModelForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['name', 'comment']
        labels = {
            'name': '',
            'comment': 'Comment',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ''}),
            'comment': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ''}),
        }


class ViewOrderModelForm(BaseOrderModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs['hidden'] = True
        self.fields['comment'].widget.attrs['disabled'] = True


class EditOrderModelForm(ViewOrderModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['comment'].widget.attrs['disabled'] = False


class BaseOrderItemModelForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['id', 'order', 'client', 'product', 'quantity']
        labels = {
            'order': '',
            'client': 'Client',
            'product': 'Product',
            'quantity': 'Quantity',
        }
        widgets = {
            'id': forms.HiddenInput(),
            'order': forms.Select(attrs={'class': 'form-control'}),
            'client': forms.Select(attrs={'class': 'form-control'}),
            'product': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 100000,
                'step': 1
            }),
        }


class ViewOrderItemModelForm(BaseOrderItemModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['order'].widget.attrs['hidden'] = True
        self.fields['client'].widget.attrs['disabled'] = True
        self.fields['product'].widget.attrs['disabled'] = True
        self.fields['quantity'].widget.attrs['disabled'] = True


class EditOrderItemModelForm(ViewOrderItemModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['quantity'].widget.attrs['disabled'] = False
        self.fields['client'].widget.attrs['disabled'] = False
        self.fields['product'].widget.attrs['disabled'] = False


ViewOrderItemFormSet = forms.modelformset_factory(
    OrderItem,
    form=ViewOrderItemModelForm,
    extra=0,
)


EditOrderItemFormSet = forms.modelformset_factory(
    OrderItem,
    form=EditOrderItemModelForm,
    can_delete=True,
)
