import logging
from datetime import datetime
from itertools import groupby

from django.db import models
from django.dispatch import receiver

from .directories import Supplier, Product, Client
from .confirmations import Confirmation, ConfirmationItem
from .orders import Order
from .cancellations import CancellationItem


log = logging.getLogger(__name__)


class Invoice(models.Model):
    id = models.CharField(primary_key=True, null=False, max_length=450)
    name = models.CharField(max_length=250)
    invoice_date = models.DateField(default=datetime.today)
    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, related_name="invoices")
    comment = models.CharField(
        max_length=450, null=True, blank=True, default=None)

    @property
    def total_amount(self):
        return sum(item.total_amount for item in self.items.all())

    class Meta:
        ordering = ['-invoice_date']

    @staticmethod
    def name_into_id(filename):
        filename_without_extension = ".".join(filename.split(".")[:-1])
        name_starts = filename_without_extension.upper().split(
            ' ', maxsplit=2)[1].strip()
        name_ends = "".join(filename_without_extension.upper().split(" ")[2])
        return "-".join([name_starts, name_ends])


@receiver(models.signals.pre_save, sender=Invoice)
def set_id(sender, instance, **kwargs):
    if not instance.id:
        instance.id = instance.name_into_id(instance.name)


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="invoiced")
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="invoiced_products")
    confirmation = models.ForeignKey(Confirmation,
                                     on_delete=models.SET_NULL, related_name="invoiced_items", null=True, default=None)
    order = models.ForeignKey(Order,
                              on_delete=models.SET_NULL, related_name="invoiced_items", null=True, default=None)
    comment = models.CharField(
        max_length=450, null=True, blank=True, default=None)

    class Meta:
        unique_together = ("invoice", "client", "product",
                           "confirmation", "order")

    @property
    def total_amount(self):
        if self.price and self.quantity:
            return self.price * self.quantity
        return 0

    @classmethod
    def save_invoice_items(cls, invoice_data_json, invoice):  # pylint: disable=R0914
        from .report import get_left_quantity_per_client
        filtered_data = [
            item for item in invoice_data_json if item['product'] != ""]

        sorted_data = sorted(filtered_data,
                             key=lambda x: x['product'])
        grouped = groupby(sorted_data, key=lambda x: x['product'])
        for product_id, group in grouped:
            items = list(group)
            total_quantity = sum(int(item['quantity']) for item in items)
            product_id = items[0].get("product")
            brand_id = product_id.split("_")[1]
            product_name = items[0].get("product_name")
            defaults = {
                'name': product_name,
                'brand_id': brand_id

            }
            product, created = Product.objects.get_or_create(
                id=product_id, defaults=defaults)
            price = items[0].get("price")
            confirmed_items = ConfirmationItem.objects.filter(
                product_id=product_id,
                confirmation__confirmation_date__lte=invoice.invoice_date)\
                .select_related("confirmation", "order")\
                .order_by(
                    "order__order_date",
                    "confirmation__confirmation_date",
            )
            invoiced_items = InvoiceItem.objects.filter(
                product_id=product_id,
            )
            cancelled_items = CancellationItem.objects.filter(
                product_id=product_id,
            )
            left_quantity_per_client = get_left_quantity_per_client(product_id,
                                                                    confirmed_items, invoiced_items, cancelled_items)
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
                    cls.objects.create(
                        invoice_id=invoice.id,
                        client_id=item['client_id'],
                        product_id=product.id,
                        confirmation_id=item['confirmation_id'],
                        order_id=item['order_id'],
                        quantity=quantity,
                        price=price)
            if total_quantity > 0:
                client, _ = Client.objects.get_or_create(id="Unknown")
                cls.objects.create(
                    invoice_id=invoice.id,
                    client_id=client.id,
                    product_id=product_id,
                    quantity=total_quantity,
                    price=price,)
