import logging
from decimal import Decimal
from datetime import date

import pytest
from django.urls import reverse

from ...models.invoices import (
    Invoice,
    InvoiceItem,
)

log = logging.getLogger(__name__)


@pytest.mark.parametrize("value,expected", [
    ("INVOICE0-010125", True),
    ("INVOICE10-010125", False),
])
@pytest.mark.django_db
def test_invoice_delete(value, expected, client, invoices):
    url = reverse('deleteinvoice', kwargs={'pk': value})
    response = client.get(url)
    assert Invoice.objects.filter(pk=value).exists() == expected


@pytest.mark.django_db
def test_invoice_update(client, invoices, invoiceitems, confirmations):
    invoice_id = "INVOICE0-010125"
    forms_amount = InvoiceItem.objects.filter(
        invoice=invoice_id).count()
    url = reverse('editinvoice', kwargs={'pk': invoice_id})
    response = client.get(url)
    data = {
        'save': [''],
        'csrfmiddlewaretoken': response.context['csrf_token'],
        'form-TOTAL_FORMS':  forms_amount+1,
        'form-INITIAL_FORMS': forms_amount,
        'form-MIN_NUM_FORMS': '0',
        'form-MAX_NUM_FORMS': '1000',
        'name': invoices.get("0").name,
        'comment': 'Test comment',
        'form-0-client': [invoiceitems.get("0").client.id],
        'form-0-product': [invoiceitems.get("0").product.id],
        'form-0-quantity': [invoiceitems.get("0").quantity-6],
        'form-0-confirmation': [invoiceitems.get("0").confirmation.id],
        'form-0-order': [invoiceitems.get("0").order.id],
        'form-0-price': [invoiceitems.get("0").price],
        'form-0-id': [invoiceitems.get("0").id],
        'form-1-client': [invoiceitems.get("1").client.id],
        'form-1-product': [invoiceitems.get("1").product.id],
        'form-1-quantity': [invoiceitems.get("1").quantity],
        'form-1-confirmation': [invoiceitems.get("1").confirmation.id],
        'form-1-order': [invoiceitems.get("1").order.id],
        'form-1-price': [invoiceitems.get("1").price],
        'form-1-id': [invoiceitems.get("1").id],
        'form-2-client': [invoiceitems.get("1").client.id],
        'form-2-product': [invoiceitems.get("0").product.id],
        'form-2-confirmation': [''],
        'form-2-order': [''],
        'form-2-quantity': [6],
        'form-2-price': [invoiceitems.get("0").price],
        'form-2-id': [''],
    }
    response = client.post(url, data)
    updated_invoice = Invoice.objects.get(pk=invoice_id)
    updated_items = list(InvoiceItem.objects.filter(
        invoice=invoice_id).order_by('id').values(
            'invoice_id',
            'client_id',
            'comment',
            'product_id',
            'confirmation_id',
            'order_id',
            'quantity',
            'price',
            'order_id'))
    updated_items_expected = [{
        'invoice_id': "INVOICE0-010125",
        'client_id': 'C0',
        'comment': None,
        'product_id': 'TESTPRODUCT0_B0',
        'confirmation_id': confirmations.get("0").id,
        'order_id': confirmations.get("0").order.all()[0].id,
        'quantity': 4,
        'price': Decimal('0.10'),
    },
        {'invoice_id': "INVOICE0-010125",
         'client_id': 'C1',
         'comment': None,
         'product_id': 'TESTPRODUCT1_B0',
         'confirmation_id': confirmations.get("0").id,
         'order_id': confirmations.get("0").order.all()[1].id,
         'quantity': 20,
         'price': Decimal('10.10'),
         },
        {'invoice_id': "INVOICE0-010125",
         'client_id': 'C1',
         'comment': None,
         'product_id': 'TESTPRODUCT0_B0',
         'confirmation_id': None,
         'order_id': None,
         'quantity': 6,
         'price': Decimal('0.10'),
         },
    ]
    assert updated_invoice == invoices.get("0")
    assert updated_invoice.comment == "Test comment"
    assert len(updated_items) == 3
    assert updated_items == updated_items_expected


@pytest.mark.django_db
def test_invoice_create(client, invoice_excel, supplier, confirmationitems):
    invoice_id = 'INVOICE0-010125'
    url = reverse('addinvoice')
    response = client.get(url)
    dt = invoice_excel.name.split(".")[0][-6:]
    invoice_date = f"20{dt[4:6]}-{dt[2:4]}-{dt[:2]}"
    data = {
        'csrfmiddlewaretoken': response.context['csrf_token'],
        'name': [invoice_excel.name],
        'invoice_date': [invoice_date],
        'initial-invoice_date': [date.today()],
        'supplier': [supplier.id],
        'comment': [''],
        'action': ['preview'],
        'file': [invoice_excel]
    }
    response = client.post(url, data=data,)
    response = client.get(url)
    data.update({
        'csrfmiddlewaretoken': response.context['csrf_token'],
        'initial-invoice_date': [invoice_date],
        'file': [''],
        'action': ['add'],
    })
    response = client.post(url, data=data)
    new_invoice = Invoice.objects.filter(pk=invoice_id)
    new_items = list(InvoiceItem.objects.filter(
        invoice=invoice_id).order_by('id').values(
            'invoice_id',
            'client_id',
            'comment',
            'product_id',
            'quantity',
            'price',
            'confirmation_id',
            'order_id'))
    expected_invoice = [{
        'id': "INVOICE0-010125",
        'name': "Test Invoice0 010125.xslx",
        'invoice_date': date(2025, 1, 1),
        'supplier_id': 'T00016',
        'comment': None
    }]
    expected_items = [
        {'invoice_id': 'INVOICE0-010125',
         'client_id': 'C0',
         'product_id': 'TESTPRODUCT0_B0',
         'quantity': 10,
         'price': Decimal('10.10'),
         'order_id': confirmationitems.get("0").order.id,
         'confirmation_id': confirmationitems.get("0").confirmation.id,
         'comment': None},
        {'invoice_id': 'INVOICE0-010125',
         'client_id': 'C1',
         'product_id': 'TESTPRODUCT1_B0',
         'quantity': 20,
         'price': Decimal('20.02'),
         'order_id': confirmationitems.get("1").order.id,
         'confirmation_id': confirmationitems.get("1").confirmation.id,
         'comment': None}
    ]
    assert new_invoice.exists()
    assert list(new_invoice.values()) == expected_invoice
    assert new_items == expected_items


@pytest.mark.django_db
def test_invoice_view(client, invoices, invoiceitems):
    invoice_id = "INVOICE0-010125"
    url = reverse('viewinvoice', kwargs={'pk': invoice_id})
    response = client.get(url)
    assert response.status_code == 200
    assert invoices.get("0").id.encode() in response.content
    assert invoices.get("0").name.encode() in response.content
    for item in InvoiceItem.objects.filter(invoice_id=invoice_id):
        assert item.product.id.encode() in response.content
        assert item.client.id.encode() in response.content
        assert str(item.quantity).encode() in response.content
        assert str(item.price).encode() in response.content
    url = reverse('exportinvoicetoexcel', kwargs={'pk': invoice_id})
    response = client.post(url)
    assert response.status_code == 200
    assert 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in response['Content-Type']
    assert f'attachment; filename="data-{invoice_id}.xlsx"' in response['Content-Disposition']


@pytest.mark.django_db
def test_invoice_list_view(client, invoices):
    url = reverse('invoices')
    response = client.get(url)
    assert response.status_code == 200
    for invoice in invoices.values():
        assert invoice.id.encode() in response.content
        assert invoice.name.encode() in response.content
