import logging
from datetime import date

from django import forms
from django.core.exceptions import ValidationError

from ..models.directories import (
    Product,
)
from ..models.confirmations import (
    Confirmation,
    ConfirmationItem,
)
from ..models.cancellations import (
    Cancellation,
    CancellationItem,
)

log = logging.getLogger(__name__)


class CancellationModelForm(forms.ModelForm):
    cancellation_data = forms.CharField(
        label='Cancellation data',
        widget=forms.Textarea(
            attrs={'class': 'form-control', 'placeholder': 'Input cancellation data:\nOrder\nItem\nQty\n'})
    )

    class Meta:
        model = Cancellation
        fields = ['cancellation_date', 'supplier', 'brand', 'comment']
        labels = {
            'cancellation_date': 'Date',
            'supplier': 'Supplier',
            'brand': 'Brand',
            'comment': 'Comment',
        }
        widgets = {
            'cancellation_date': forms.DateInput(attrs={'class': 'form-control', 'placeholder': 'Input invoice date'}),
            'supplier': forms.Select(attrs={'class': 'form-control'}),
            'brand': forms.Select(attrs={'class': 'form-control'}),
            'comment': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Input comment'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['supplier'].initial = "T00016"
        self.fields['cancellation_date'].initial = date.today().strftime(
            '%Y-%m-%d')

    def clean_cancellation_date(self):
        cancellation_date = self.cleaned_data.get('cancellation_date')
        if cancellation_date > date.today():
            raise ValidationError("Cancellation date must be past")
        return cancellation_date

    def clean_cancellation_data(self):  # pylint: disable=R0912
        cancellation_data = self.cleaned_data.get('cancellation_data')
        brand = self.cleaned_data.get('brand')
        cancellation_list = cancellation_data.split("\r\n")
        dict_keys = [x.lower() for x in cancellation_list[:3]
                     if x.lower() in ["order", "item", "qty"]]
        if len(cancellation_list) % len(dict_keys):
            raise ValidationError("Invalid data size")
        result = []
        i = len(dict_keys)
        while i < len(cancellation_list):
            cancellation_dict = {}
            for j, key in enumerate(dict_keys):
                item = {}
                value = cancellation_list[i+j]
                if key == "item":
                    if brand.id == "B05":
                        value = value.zfill(14)
                    product_id = f'{value}_{brand.id}'
                    if not Product.objects.filter(id=product_id).exists():
                        raise ValidationError("Invalid item")
                    item = {'product': product_id}
                elif key == "qty":
                    try:
                        if int(value) > 0:
                            item = {'quantity': int(value)}
                        else:
                            raise ValidationError("Invalid qty")
                    except Exception as e:
                        raise ValidationError("Invalid qty") from e
                elif key == "order":
                    if not Confirmation.objects.filter(id=value).exists():
                        raise ValidationError("Invalid confirmation")
                    if not "item" in dict_keys:
                        if "qty" in dict_keys:
                            raise ValidationError(
                                "Qty does not make sense without item")
                        cancellation_dicts = ConfirmationItem.objects.filter(
                            confirmation_id=value).values("confirmation", "product").distinct()
                        result += cancellation_dicts
                    else:
                        item = {'confirmation': value}
                if item:
                    cancellation_dict.update(item)
                    if cancellation_dict not in result:
                        result.append(cancellation_dict)
            i += len(dict_keys)
        if not cancellation_data:
            raise ValidationError("No data")
        return result


class BaseConfirmationItemModelForm(forms.ModelForm):

    class Meta:
        model = CancellationItem
        fields = ['client', 'product', 'quantity', 'order', 'confirmation']
        labels = {
            'client': 'Client',
            'product': 'Product',
            'quantity': 'Quantity',
            'order': 'Order',
            'confirmation': 'Confirmation',
        }
        widgets = {
            'product': forms.Select(attrs={
                'style': 'width: 180px',
                'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={
                'style': 'width: 80px',
                'class': 'form-control',
                'min': 1,
                'max': 100000,
                'step': 1
            }),
            'price':  forms.NumberInput(attrs={
                'style': 'width: 100px',
                'class': 'form-control'}),
            'client': forms.Select(attrs={
                'style': 'width: 130px',
                'class': 'form-control'}),
            'order': forms.TextInput(attrs={
                'style': 'width: 350px',
                'class': 'form-control',
                'placeholder': ""}),
            'confirmation': forms.TextInput(attrs={
                'style': 'width: 350px',
                'class': 'form-control',
                'placeholder': ""}),
        }
