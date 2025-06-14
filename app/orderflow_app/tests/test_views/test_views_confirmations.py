import logging
from decimal import Decimal
from datetime import date

import pytest
from django.urls import reverse

from ...models.confirmations import (
    Confirmation,
    ConfirmationItem,
)

log = logging.getLogger(__name__)


@pytest.mark.parametrize("value,expected", [
    ("T0", True),
    ("T10", False),
])
@pytest.mark.django_db
def test_confirmation_delete(value, expected, client, confirmations):
    url = reverse('deleteconfirmation', kwargs={'pk': value})
    response = client.get(url)
    assert Confirmation.objects.filter(pk=value).exists() == expected


@pytest.mark.django_db
def test_confirmation_update(client, confirmations, confirmationitems):
    confirmation_id = "T0"
    forms_amount = ConfirmationItem.objects.filter(
        confirmation=confirmation_id).count()
    url = reverse('editconfirmation', kwargs={'pk': confirmation_id})
    response = client.get(url)
    data = {
        'save': [''],
        'csrfmiddlewaretoken': response.context['csrf_token'],
        'form-TOTAL_FORMS':  forms_amount+1,
        'form-INITIAL_FORMS': forms_amount,
        'form-MIN_NUM_FORMS': '0',
        'form-MAX_NUM_FORMS': '1000',
        'name': confirmations.get("0").name,
        'order': [order.id for order in confirmations.get("0").order.all()],
        'comment': 'Test comment',
        'form-0-client': [confirmationitems.get("0").client.id],
        'form-0-product': [confirmationitems.get("0").product.id],
        'form-0-order': [confirmationitems.get("0").order.id],
        'form-0-quantity': [confirmationitems.get("0").quantity-6],
        'form-0-price': [confirmationitems.get("0").price],
        'form-0-id': [confirmationitems.get("0").id],
        'form-1-client': [confirmationitems.get("1").client.id],
        'form-1-product': [confirmationitems.get("1").product.id],
        'form-1-order': [confirmationitems.get("1").order.id],
        'form-1-quantity': [confirmationitems.get("1").quantity],
        'form-1-price': [confirmationitems.get("1").price],
        'form-1-id': [confirmationitems.get("1").id],
        'form-2-client': [confirmationitems.get("1").client.id],
        'form-2-product': [confirmationitems.get("0").product.id],
        'form-2-order': [confirmationitems.get("1").order.id],
        'form-2-quantity': [6],
        'form-2-price': [confirmationitems.get("0").price],
        'form-2-id': [''],
    }
    response = client.post(url, data)
    updated_confirmation = Confirmation.objects.get(pk=confirmation_id)
    updated_items = list(ConfirmationItem.objects.filter(
        confirmation=confirmation_id).order_by('id').values(
            'confirmation_id',
            'client_id',
            'comment',
            'product_id',
            'quantity',
            'price',
            'order_id'))
    updated_items_expected = [{
        'confirmation_id': "T0",
        'client_id': 'C0',
        'comment': None,
        'product_id': 'TESTPRODUCT0_B0',
        'quantity': 4,
        'price': Decimal('0.10'),
        'order_id': confirmations.get("0").order.all()[0].id,
    },
        {'confirmation_id': "T0",
         'client_id': 'C1',
         'comment': None,
         'product_id': 'TESTPRODUCT1_B0',
         'quantity': 20,
         'price': Decimal('10.10'),
         'order_id': confirmations.get("0").order.all()[1].id,
         },
        {'confirmation_id': "T0",
         'client_id': 'C1',
         'comment': None,
         'product_id': 'TESTPRODUCT0_B0',
         'quantity': 6,
         'price': Decimal('0.10'),
         'order_id': confirmations.get("0").order.all()[1].id,
         },
    ]
    assert updated_confirmation == confirmations.get("0")
    assert updated_confirmation.comment == "Test comment"
    assert len(updated_items) == 3
    assert updated_items == updated_items_expected


@pytest.mark.django_db
def test_confirmation_create(client, confirmation_excel, orders, supplier, orderitems):
    confirmation_id = 'T3'
    url = reverse('addconfirmation')
    response = client.get(url)
    dt = confirmation_excel.name.split(".")[0][-6:]
    confirmation_date = f"20{dt[4:6]}-{dt[2:4]}-{dt[:2]}"
    data = {
        'csrfmiddlewaretoken': response.context['csrf_token'],
        'name': [confirmation_excel.name],
        'confirmation_date': [confirmation_date],
        'initial-confirmation_date': [date.today()],
        'confirmation_code': ['Preview'],
        'supplier': [supplier.id],
        'order': [orders.get('0').id],
        'comment': [''],
        'action': ['preview'],
        'file': [confirmation_excel]
    }
    response = client.post(url, data=data,)
    response = client.get(url)
    data.update({
        'csrfmiddlewaretoken': response.context['csrf_token'],
        'confirmation_code': [confirmation_id],
        'initial-confirmation_date': [confirmation_date],
        'file': [''],
        'action': ['add'],
    })
    response = client.post(url, data=data)
    new_confirmation = Confirmation.objects.filter(pk=confirmation_id)
    new_items = list(ConfirmationItem.objects.filter(
        confirmation=confirmation_id).order_by('id').values(
            'confirmation_id',
            'client_id',
            'comment',
            'product_id',
            'quantity',
            'price',
            'order_id'))
    expected_confirmation = [{
        'id': "T3",
        'confirmation_code': 'T3',
        'name': "Confirmation B0 010125.xlsx",
        'confirmation_date': date(2025, 1, 1),
        'supplier_id': 'T00016',
        'comment': None
    }]
    expected_items = [
        {'confirmation_id': 'T3',
         'client_id': 'C0',
         'product_id': 'TESTPRODUCT0_B0',
         'quantity': 10,
         'price': Decimal('10.10'),
         'order_id': orders.get("0").id,
         'comment': None},
        {'confirmation_id': 'T3',
         'client_id': 'C1',
         'product_id': 'TESTPRODUCT1_B0',
         'quantity': 20,
         'price': Decimal('20.02'),
         'order_id': orders.get("0").id,
         'comment': None}
    ]
    assert new_confirmation.exists()
    assert list(new_confirmation.values()) == expected_confirmation
    assert new_items == expected_items


@pytest.mark.django_db
def test_confirmation_view(client, confirmations, confirmationitems):
    confirmation_id = "T0"
    url = reverse('viewconfirmation', kwargs={'pk': confirmation_id})
    response = client.get(url)
    assert response.status_code == 200
    assert confirmations.get("0").id.encode() in response.content
    assert confirmations.get("0").name.encode() in response.content
    for item in ConfirmationItem.objects.filter(confirmation_id=confirmation_id):
        assert item.product.id.encode() in response.content
        assert item.client.id.encode() in response.content
        assert str(item.quantity).encode() in response.content
        assert str(item.price).encode() in response.content
    url = reverse('exportconfirmationtoexcel', kwargs={'pk': confirmation_id})
    response = client.post(url)
    assert response.status_code == 200
    assert 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in response['Content-Type']
    assert f'attachment; filename="data-{confirmation_id}.xlsx"' in response['Content-Disposition']


@pytest.mark.django_db
def test_confirmation_list_view(client, confirmations):
    url = reverse('confirmations')
    response = client.get(url)
    assert response.status_code == 200
    for confirmation in confirmations.values():
        assert confirmation.id.encode() in response.content
        assert confirmation.name.encode() in response.content
