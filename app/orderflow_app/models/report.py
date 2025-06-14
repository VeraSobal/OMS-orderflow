import logging
from io import BytesIO

import pandas as pd
from django.db import models

from .directories import Product, Client
from .orders import Order
from .confirmations import Confirmation, ConfirmationItem

log = logging.getLogger(__name__)


def get_left_quantity_per_client(product_id, confirmed_items, invoiced_items, cancelled_items):
    confirmed_quantity_per_client = confirmed_items.values('client_id', 'confirmation_id', 'order_id').annotate(
        quantity=models.Sum('quantity')
    )
    invoiced_quantity_per_client = invoiced_items.values('client_id', 'confirmation_id', 'order_id').annotate(
        quantity=models.Sum('quantity')
    )
    cancelled_quantity_per_client = cancelled_items.values('client_id', 'confirmation_id', 'order_id').annotate(
        quantity=models.Sum('quantity')
    )
    confirmed_quantity = confirmed_quantity_per_client.order_by('client_id').aggregate(
        total=models.Sum("quantity", default=0))['total']
    invoiced_quantity = invoiced_quantity_per_client.order_by('client_id').aggregate(
        total=models.Sum("quantity", default=0))['total']
    cancelled_quantity = cancelled_quantity_per_client.order_by('client_id').aggregate(
        total=models.Sum("quantity", default=0))['total']
    left_quantity_per_client = []
    if confirmed_quantity-invoiced_quantity-cancelled_quantity > 0:
        for confirmed_item in confirmed_quantity_per_client:
            total_invoiced = sum(invoiced_item.get('quantity') for invoiced_item in invoiced_quantity_per_client
                                 if invoiced_item.get('client_id') == confirmed_item.get('client_id') and
                                 invoiced_item.get('order_id') == confirmed_item.get('order_id') and
                                 invoiced_item.get('confirmation_id') == confirmed_item.get('confirmation_id'))
            total_cancelled = sum(cancelled_item.get('quantity') for cancelled_item in cancelled_quantity_per_client
                                  if cancelled_item.get('client_id') == confirmed_item.get('client_id') and
                                  cancelled_item.get('order_id') == confirmed_item.get('order_id') and
                                  cancelled_item.get('confirmation_id') == confirmed_item.get('confirmation_id'))
            left_quantity = confirmed_item["quantity"] - \
                total_invoiced-total_cancelled
            if left_quantity > 0:
                left_quantity_per_client.append(
                    {"product_id": product_id,
                        "client_id": confirmed_item["client_id"],
                        "order_id": confirmed_item["order_id"],
                        "confirmation_id": confirmed_item["confirmation_id"],
                        "quantity": left_quantity})
    return left_quantity_per_client


def get_balance(item=None):
    from .invoices import InvoiceItem  # pylint: disable=R0401
    from .cancellations import CancellationItem  # pylint: disable=R0401
    if item is None:
        item = {}
    products = Product.objects.values_list("id", flat=True)
    confirmation_id = item.get("confirmation")
    order_id = item.get("order")
    result = []
    for product_id in products:
        confirmation = ({'confirmation_id': confirmation_id}
                        if confirmation_id is not None else {})
        order = ({'order_id': order_id}
                 if order_id is not None else {})
        confirmed_items = ConfirmationItem.objects.filter(
            **order,
            **confirmation,
            product_id=product_id,
        )\
            .select_related("confirmation", "order")\
            .order_by(
                "order__order_date",
                "confirmation__confirmation_date",
        )
        invoiced_items = InvoiceItem.objects.filter(
            **order,
            **confirmation,
            product_id=product_id,
        )
        cancelled_items = CancellationItem.objects.filter(
            **order,
            **confirmation,
            product_id=product_id,
        )
        left_quantity_per_client = get_left_quantity_per_client(
            product_id, confirmed_items, invoiced_items, cancelled_items)
        report_item = [{"product": Product.objects.get(id=x["product_id"]).id,
                        "confirmation": Confirmation.objects.get(id=x["confirmation_id"]).name,
                        "order": Order.objects.get(id=x["order_id"]).name,
                        "client": Client.objects.get(id=x["client_id"]).id,
                        "quantity": x["quantity"]}
                       for x in left_quantity_per_client]
        result += report_item
    return sorted(result, key=lambda x: (x['product'], x['confirmation'], x['client']))


def export_to_excel(data):
    df = pd.DataFrame(
        data
    )
    if df.empty:
        return None
    excel_file = BytesIO()
    df.to_excel(excel_file, index=False)
    excel_file.seek(0)
    return excel_file
