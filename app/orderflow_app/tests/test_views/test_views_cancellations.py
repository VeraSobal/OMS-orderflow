import logging
from datetime import date, datetime

import pytest
from django.urls import reverse

from ...models.cancellations import (
    Cancellation,
    CancellationItem,
)

log = logging.getLogger(__name__)


@pytest.mark.parametrize("value,expected", [
    ("0", True),
    ("1", False),
])
@pytest.mark.django_db
def test_cancellation_delete(value, expected, client, cancellation):
    url = reverse('deletecancellation', kwargs={'pk': value})
    response = client.get(url)
    assert Cancellation.objects.filter(pk=value).exists() == expected


@pytest.mark.django_db
def test_cancellation_create(client, supplier, brands, confirmationitems):
    cancellation_id = 1
    url = reverse('addcancellation')
    response = client.get(url)
    cancellation_date = "2025-01-01"
    data = {
        'csrfmiddlewaretoken': response.context['csrf_token'],
        'cancellation_date': [cancellation_date],
        'initial-cancellation_date': [date.today()],
        'supplier': [supplier.id],
        'brand': [brands.get("0").id],
        'comment': [''],
        'action': ['add'],
        'cancellation_data': ['Order\r\nItem\r\nQty\r\nT0\r\nTESTPRODUCT0\r\n1\r\nT1\r\nTESTPRODUCT1\r\n2']
    }
    response = client.post(url, data=data,)
    new_cancellation = Cancellation.objects.filter(id=cancellation_id)
    new_items = list(CancellationItem.objects.filter(
        cancellation_id=cancellation_id).order_by('id').values(
            'cancellation_id',
            'client_id',
            'product_id',
            'confirmation_id',
            'order_id',
            'quantity',))
    expected_cancellation = [{
        'id': 1,
        'cancellation_date': date(2025, 1, 1),
        'supplier_id': 'T00016',
        'brand_id': 'B0',
        'comment': None
    }]
    assert new_cancellation.exists()
    assert list(new_cancellation.values()) == expected_cancellation
    expected_items = [
        {'cancellation_id': cancellation_id,
         'client_id': confirmationitems.get("0").client.id,
         'product_id': confirmationitems.get("0").product.id,
         'quantity': 1,
         'order_id': confirmationitems.get("0").order.id,
         'confirmation_id': confirmationitems.get("0").confirmation.id,
         },
        {'cancellation_id': cancellation_id,
         'client_id': confirmationitems.get("3").client.id,
         'product_id': confirmationitems.get("3").product.id,
         'quantity': 2,
         'order_id': confirmationitems.get("3").order.id,
         'confirmation_id': confirmationitems.get("3").confirmation.id,
         }
    ]
    assert new_items == expected_items


@pytest.mark.django_db
def test_cancellation_list_view(client, cancellationitem):
    url = reverse('cancellations')
    response = client.get(url)
    assert response.status_code == 200
    assert str(cancellationitem.quantity).encode() in response.content
    assert cancellationitem.client.id.encode() in response.content
    assert cancellationitem.order.name.encode() in response.content
    assert cancellationitem.confirmation.id.encode() in response.content
    assert datetime.strptime(cancellationitem.cancellation.cancellation_date,
                             '%Y-%m-%d').strftime('%d-%m-%Y').encode() in response.content
