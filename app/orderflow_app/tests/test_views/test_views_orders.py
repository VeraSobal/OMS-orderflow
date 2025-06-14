import logging
from datetime import date

import pytest
from django.urls import reverse

from ...models.orders import (
    Order,
    OrderItem,
)

log = logging.getLogger(__name__)


@pytest.mark.parametrize("value,expected", [
    ("Order 0-C0-B0-S0-01-01-2025", True),
    ("Order 10-C0-B0-S0-01-01-2025", False),
])
@pytest.mark.django_db
def test_order_delete(value, expected, client, orders):
    url = reverse('deleteorder', kwargs={'pk': value})
    response = client.get(url)
    assert Order.objects.filter(pk=value).exists() == expected


@pytest.mark.django_db
def test_order_update(client, orders, orderitems):
    order_id = "Order 0-C0-B0-S0-01-01-2025"
    forms_amount = OrderItem.objects.filter(order=order_id).count()
    url = reverse('editorder', kwargs={'pk': order_id})
    response = client.get(url)
    data = {
        'save': [''],
        'csrfmiddlewaretoken': response.context['csrf_token'],
        'form-TOTAL_FORMS': forms_amount+1,
        'form-INITIAL_FORMS': forms_amount,
        'form-MIN_NUM_FORMS': '0',
        'form-MAX_NUM_FORMS': '1000',
        'name': orders.get("0").name,
        'comment': 'Test comment',
        'form-0-order': [order_id],
        'form-0-client': [orderitems.get("0").client.id],
        'form-0-product': [orderitems.get("0").product.id],
        'form-0-quantity': [orderitems.get("0").quantity],
        'form-0-id': [orderitems.get("0").id],
        'form-0-DELETE': 'on',
        'form-1-order': [order_id],
        'form-1-client': [orderitems.get("1").client.id],
        'form-1-product': [orderitems.get("1").product.id],
        'form-1-quantity': [30],
        'form-1-id': [orderitems.get("1").id],
        'form-2-order': [order_id],
        'form-2-client':  [''],
        'form-2-product':  [''],
        'form-2-quantity': [''],
        'form-2-id': [''],
    }
    response = client.post(url, data)
    updated_order = Order.objects.get(pk=order_id)
    updated_items = list(OrderItem.objects.filter(
        order=order_id).values("order_id", "client_id", "product_id", "quantity"))
    updated_items_expected = [{
        'order_id': "Order 0-C0-B0-S0-01-01-2025",
        'client_id': 'C1',
        'product_id': 'TESTPRODUCT1_B0',
        'quantity': 30,
    }]
    assert updated_order == orders.get("0")
    assert updated_order.comment == "Test comment"
    assert len(updated_items) == 1
    assert updated_items == updated_items_expected


@pytest.mark.django_db
def test_order_create(client, order_excel, clients, supplier):
    url = reverse('addorder')
    response = client.get(url)
    file_name_splitted = order_excel.name.split(".")[0].split("-")
    order_date = "-".join(file_name_splitted[:3:-1])
    supplier_id = file_name_splitted[3]
    data = {
        'csrfmiddlewaretoken': response.context['csrf_token'],
        'name': [order_excel.name],
        'order_date': order_date,
        'supplier': [supplier_id],
        'comment': [''],
        'action': ['preview'],
        'file': order_excel
    }
    response = client.post(url, data=data,)
    response = client.get(url)
    data.update({
        'csrfmiddlewaretoken': response.context['csrf_token'],
        'file': [''],
        'action': ['add'],
    })
    response = client.post(url, data=data)
    order_id = Order.name_into_id(order_excel.name)
    new_order = Order.objects.filter(pk=order_id)
    new_items = list(OrderItem.objects.filter(order=order_id).order_by('id').values(
        "order_id", "client_id", "product_id", "quantity"))
    expected_order = [{
        'id': "Order 3-C0-B0-T00016-01-01-2025",
        'name': "Order 3-C0-B0-T00016-01-01-2025.xlsx",
        'order_date': date(2025, 1, 1),
        'supplier_id': 'T00016',
        'comment': None
    }]
    expected_items = [
        {'order_id': 'Order 3-C0-B0-T00016-01-01-2025',
         'client_id': 'C0',
         'product_id': 'P0_B0',
         'quantity': 10},
        {'order_id': 'Order 3-C0-B0-T00016-01-01-2025',
         'client_id': 'C1',
         'product_id': 'P1_B0',
         'quantity': 20}]
    assert new_order.exists()
    assert list(new_order.values()) == expected_order
    assert new_items == expected_items


@pytest.mark.django_db
def test_order_view(client, orders, orderitems):
    order_id = "Order 0-C0-B0-S0-01-01-2025"
    url = reverse('vieworder', kwargs={'pk': order_id})
    response = client.get(url)
    assert response.status_code == 200
    assert orders.get("0").id.encode() in response.content
    assert orders.get("0").name.encode() in response.content
    for item in OrderItem.objects.filter(order_id=order_id):
        assert item.product.id.encode() in response.content
        assert item.client.id.encode() in response.content
        assert str(item.quantity).encode() in response.content


@pytest.mark.django_db
def test_order_list_view(client, orders):
    url = reverse('orders')
    response = client.get(url)
    assert response.status_code == 200
    for order in orders.values():
        assert order.id.encode() in response.content
        assert order.name.encode() in response.content
