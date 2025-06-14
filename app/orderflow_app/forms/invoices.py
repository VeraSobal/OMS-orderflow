import logging
from datetime import date
from io import BytesIO

import pandas as pd
from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseModelFormSet
from django.db.models import Sum

from ..models.directories import (
    Product,
)
from ..models.invoices import (
    Invoice,
    InvoiceItem,
)

log = logging.getLogger(__name__)


class InvoiceModelForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['name', 'invoice_date', 'supplier', 'comment']
        labels = {
            'name': 'Name',
            'invoice_date': 'Date',
            'supplier': 'Supplier',
            'comment': 'Comment',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Input invoice name'}),
            'invoice_date': forms.DateInput(attrs={'class': 'form-control', 'placeholder': 'Input invoice date'}),
            'supplier': forms.Select(attrs={'class': 'form-control'}),
            'comment': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Input comment'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['supplier'].initial = "T00016"

    def clean_invoice_date(self):
        invoice_date = self.cleaned_data.get('invoice_date')
        if invoice_date > date.today():
            raise ValidationError("invoice date must be past")
        return invoice_date

    def clean_name(self):
        name = self.cleaned_data.get('name')
        invoice_id = Invoice.name_into_id(name)
        try:
            Invoice.objects.get(id=invoice_id)
            raise ValidationError("There is invoice with such name")
        except Invoice.DoesNotExist:
            return name


class BaseInvoiceModelForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['name', 'comment']
        labels = {
            'name': '',
            'comment': 'Comment',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ''}),
            'comment': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ''}),
        }


class ViewInvoiceModelForm(BaseInvoiceModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs['hidden'] = True
        self.fields['comment'].widget.attrs['disabled'] = True


class EditInvoiceModelForm(ViewInvoiceModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['comment'].widget.attrs['disabled'] = False


class ProductPriceSelectWidget(forms.Select):
    def __init__(self, *args, invoice=None, **kwargs):  # pylint: disable=R0914
        super().__init__(*args, **kwargs)
        self.invoice = invoice

    def create_option(self, name, value, label, selected, index, **kwargs):  # pylint: disable=W0221,R0913,R0917
        option = super().create_option(name, value, label, selected, index, **kwargs)
        if value and self.invoice:
            try:
                invoice_item = InvoiceItem.objects.filter(
                    invoice=self.invoice,
                    product_id=value
                ).first()
                if invoice_item:
                    price = invoice_item.price
                    option['attrs']['data-price'] = f'{price}'
            except Exception as e:  # pylint: disable=W0718
                raise ValidationError(f'No price for {value} :{str(e)}') from e
        return option


class BaseInvoiceItemModelForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ['client', 'product', 'quantity',
                  'price', 'confirmation', 'order', 'comment']
        labels = {
            'client': 'Client',
            'product': 'Product',
            'quantity': 'Quantity',
            'price': 'Price',
            'confirmation': 'Confirmation',
            'order': 'Order',
            'comment': 'Comment'
        }
        widgets = {
            'product': ProductPriceSelectWidget(invoice=None, attrs={
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
            'confirmation': forms.TextInput(attrs={
                'style': 'width: 80px',
                'class': 'form-control',
                'placeholder': ""}),
            'order': forms.TextInput(attrs={
                'style': 'width: 350px',
                'class': 'form-control',
                'placeholder': ""}),
            'comment': forms.TextInput(attrs={
                'style': 'width: 150px',
                'class': 'form-control', 'placeholder': ""}),
        }


class ViewInvoiceItemModelForm(BaseInvoiceItemModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['client'].widget.attrs['disabled'] = True
        self.fields['product'].widget.attrs['disabled'] = True
        self.fields['quantity'].widget.attrs['disabled'] = True
        self.fields['price'].widget.attrs['disabled'] = True
        self.fields['confirmation'].widget.attrs['disabled'] = True
        self.fields['order'].widget.attrs['disabled'] = True
        self.fields['comment'].widget.attrs['disabled'] = True


class EditInvoiceItemModelForm(ViewInvoiceItemModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['client'].widget.attrs['disabled'] = False
        self.fields['product'].widget.attrs['disabled'] = False
        self.fields['quantity'].widget.attrs['disabled'] = False
        self.fields['price'].widget.attrs['disabled'] = False
        self.fields['price'].widget.attrs['readonly'] = True
        self.fields['confirmation'].widget.attrs['disabled'] = False
        self.fields['confirmation'].required = False
        self.fields['order'].widget.attrs['disabled'] = False
        self.fields['order'].required = False
        self.fields['comment'].widget.attrs['disabled'] = False
        self.fields['comment'].required = False


class InvoiceItemFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        invoice = kwargs.pop('form_kwargs', {}).get('invoice')
        super().__init__(*args, **kwargs)
        self.invoice = invoice
        self.queryset = InvoiceItem.objects.filter(
            invoice=invoice)
        self.deletion_widget = forms.CheckboxInput({
            'onclick': 'return confirm("Do you really want to delete the record?");'
        })
        self._initialize_widgets()

    def _initialize_widgets(self):
        products = Product.objects.filter(
            invoiced__invoice=self.invoice
        ).distinct()
        for form in self.forms:
            form.fields['product'].widget.invoice = self.invoice
            form.fields['product'].queryset = products

    def add_fields(self, form, index):
        super().add_fields(form, index)
        form.formset = self
        if not form.instance.pk:
            form.instance.invoice = self.invoice

    def get_deletion_widget(self):  # pylint: disable=W0221
        return forms.CheckboxInput(attrs={
            'title': 'delete',
        })

    def get_total(self, fieldname):
        total = 0
        for form in self.forms:
            value = getattr(form.instance, fieldname)
            if value is not None:
                total += value
        return total

    def __check_items_initial(self):
        product_quantity_dict = dict(self.invoice.items.values_list(
            'product').annotate(quantity=Sum('quantity')))
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue
            if product := form.cleaned_data.get("product"):
                quantity = form.cleaned_data.get("quantity")
                product_quantity_dict[product.id] -= quantity
        if all(value == 0 for value in product_quantity_dict.values()):
            return
        raise ValidationError(
            f"{[f'Must be {value} of {key}' for key, value in product_quantity_dict.items() if value != 0]}")

    def __check_client_product_order_confirmation_unique(self):
        client_product_order_confirmation_set = set()
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue
            client_product = (form.cleaned_data.get("client"),
                              form.cleaned_data.get("product"),
                              form.cleaned_data.get("order"),
                              form.cleaned_data.get("confirmation"),)
            if client_product in client_product_order_confirmation_set:
                raise ValidationError(
                    "Product-Client-Order must be distinct.")
            client_product_order_confirmation_set.add(client_product)

    def clean(self):
        if any(self.errors):
            return
        self.__check_items_initial()
        self.__check_client_product_order_confirmation_unique()

    def export_to_excel(self):
        df = pd.DataFrame([
            dict(form.initial.items())
            for form in self.forms
        ])
        if df.empty:
            return None
        excel_file = BytesIO()
        df.to_excel(excel_file, index=False)
        excel_file.seek(0)
        return excel_file


ViewInvoiceItemFormSet = forms.modelformset_factory(
    InvoiceItem,
    form=ViewInvoiceItemModelForm,
    formset=InvoiceItemFormSet,
    extra=0,
)


EditInvoiceItemFormSet = forms.modelformset_factory(
    InvoiceItem,
    form=EditInvoiceItemModelForm,
    formset=InvoiceItemFormSet,
    can_delete=True,
)
