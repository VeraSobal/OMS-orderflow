import logging
from datetime import datetime
from itertools import groupby

from django.db import models

from .directories import Supplier, Product, Client, Brand
from .orders import Order
from .confirmations import Confirmation, ConfirmationItem


log = logging.getLogger(__name__)


class Cancellation(models.Model):
    cancellation_date = models.DateField(default=datetime.today)
    brand = models.ForeignKey(
        Brand, on_delete=models.CASCADE, related_name="cancellations")
    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, related_name="cancellations")
    comment = models.CharField(
        max_length=450, null=True, blank=True, default=None)


class CancellationItem(models.Model):
    cancellation = models.ForeignKey(
        Cancellation, on_delete=models.CASCADE, related_name="items")
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="cancelled_products")
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="cancelled")
    confirmation = models.ForeignKey(
        Confirmation, on_delete=models.CASCADE, related_name="cancelled_items", null=True, default=None)
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="cancelled_items", null=True, default=None)
    quantity = models.PositiveIntegerField()

    @classmethod
    def save_cancellation_items(cls, cancellation_data, cancellation):  # pylint: disable=R0914
        from .report import get_left_quantity_per_client
        from .invoices import InvoiceItem  # pylint: disable=R0401
        filtered_data = [
            item for item in cancellation_data if item['product'] != ""]
        sorted_data = sorted(filtered_data,
                             key=lambda x: x['product'])
        grouped = groupby(sorted_data, key=lambda x: x['product'])
        for product_id, group in grouped:
            items = list(group)
            if items[0].get('quantity'):
                total_quantity = sum(int(item.get('quantity'))
                                     for item in items)
            else:
                total_quantity = 0
            product_id = items[0].get('product')
            for item in items:
                confirmation_id = item.get("confirmation")
                confirmation = ({'confirmation_id': confirmation_id}
                                if confirmation_id is not None else {})
                confirmed_items = ConfirmationItem.objects.filter(
                    product_id=product_id,
                    **confirmation,
                    confirmation__confirmation_date__lte=cancellation.cancellation_date)\
                    .select_related("confirmation", "order")\
                    .order_by(
                        "order__order_date",
                        "confirmation__confirmation_date",
                )
                invoiced_items = InvoiceItem.objects.filter(
                    **confirmation,
                    product_id=product_id,
                )
                cancelled_items = CancellationItem.objects.filter(
                    **confirmation,
                    cancellation=cancellation,
                    product_id=product_id,
                )
                left_quantity_per_client = get_left_quantity_per_client(
                    product_id, confirmed_items, invoiced_items, cancelled_items)
                if left_quantity_per_client:
                    i = 0
                    while i < len(left_quantity_per_client) and total_quantity > 0:
                        item = left_quantity_per_client[i]
                        i += 1
                        if total_quantity < item['quantity']:
                            quantity = total_quantity
                        else:
                            quantity = item['quantity']
                        total_quantity -= quantity
                        new_object = cls.objects.create(
                            cancellation_id=cancellation.id,
                            client_id=item['client_id'],
                            product_id=product_id,
                            confirmation_id=item['confirmation_id'],
                            order_id=item['order_id'],
                            quantity=quantity,)
            if total_quantity > 0:
                raise ValueError(
                    f"For product {product_id} quantity for cancellation is {total_quantity} pieces more than left")
