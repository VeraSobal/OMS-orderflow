import logging
from itertools import groupby
from datetime import datetime

from django.db import models
from django.dispatch import receiver

from .directories import Supplier, Client, Product
from .orders import Order, OrderItem

log = logging.getLogger(__name__)


class Confirmation(models.Model):
    id = models.CharField(primary_key=True, null=False, max_length=100)
    name = models.CharField(max_length=250)
    confirmation_code = models.CharField(max_length=10, unique=True)
    confirmation_date = models.DateField(default=datetime.today)
    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, related_name="confirmations")
    order = models.ManyToManyField(
        "Order", related_name="confirmations", null=True, default=None)
    comment = models.CharField(
        max_length=450, null=True, blank=True, default=None)

    @property
    def total_amount(self):
        return sum(item.total_amount for item in self.items.all())

    class Meta:
        ordering = ['-confirmation_date']


@receiver(models.signals.pre_save, sender=Confirmation)
def set_id(sender, instance, **kwargs):
    if not instance.id:
        instance.id = instance.confirmation_code


class ConfirmationItem(models.Model):
    confirmation = models.ForeignKey(
        Confirmation, on_delete=models.CASCADE, related_name="items")
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="confirmed_products")
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="confirmed")
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="confirmed_items", null=True, default=None)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    comment = models.CharField(
        max_length=450, null=True, blank=True, default=None)

    class Meta:
        unique_together = ("confirmation", "client", "product", "order")

    @property
    def total_amount(self):
        if self.price and self.quantity:
            return self.price * self.quantity
        return 0

    @staticmethod
    def get_left_quantity_per_client(ordered_items, confirmed_items):
        ordered_quantity_per_client = ordered_items.values('client_id').annotate(
            quantity=models.Sum('quantity')
        ).order_by('client_id')
        confirmed_quantity_per_client = confirmed_items.values('client_id').annotate(
            quantity=models.Sum('quantity')
        ).order_by('client_id')
        ordered_quantity = ordered_quantity_per_client.aggregate(
            total=models.Sum("quantity", default=0))['total']
        confirmed_quantity = confirmed_quantity_per_client.aggregate(
            total=models.Sum("quantity", default=0))['total']
        left_quantity_per_client = []
        if ordered_quantity-confirmed_quantity > 0:
            for ordered_item in ordered_quantity_per_client:
                total_confirmed = sum(confirmed_item.get('quantity') for confirmed_item in confirmed_quantity_per_client
                                      if confirmed_item.get('client_id') == ordered_item.get('client_id'))
                left_quantity = ordered_item["quantity"] - total_confirmed
                if left_quantity > 0:
                    left_quantity_per_client.append(
                        {"client_id": ordered_item["client_id"], "quantity": left_quantity})
        return left_quantity_per_client

    @classmethod
    def save_confirmation_items(cls, confirmation_data_json, confirmation):  # pylint: disable=R0914
        filtered_data = [
            item for item in confirmation_data_json if item['product'] != ""]

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
            product, created = Product.objects.update_or_create(
                id=product_id, defaults=defaults)
            price = items[0].get("price")
            orders = confirmation.order.all()
            for order in orders:
                ordered_items = OrderItem.objects.filter(
                    order=order,
                    product=product,
                ).select_related('order')
                confirmed_items = ConfirmationItem.objects.filter(
                    order=order,
                    product=product,
                ).select_related('order')
                left_quantity_per_client = cls.get_left_quantity_per_client(ordered_items,
                                                                            confirmed_items)
                if left_quantity_per_client:
                    i = 0
                    while i < len(left_quantity_per_client) and total_quantity > 0:
                        item = left_quantity_per_client[i]
                        i += 1
                        client_id = item['client_id']
                        if total_quantity < item['quantity']:
                            quantity = total_quantity
                        else:
                            quantity = item['quantity']
                        total_quantity -= quantity
                        cls.objects.create(
                            confirmation_id=confirmation.id,
                            client_id=client_id,
                            product_id=product.id,
                            order_id=order.id,
                            quantity=quantity,
                            price=price)
            if total_quantity > 0:
                client, _ = Client.objects.get_or_create(id="Unknown")
                cls.objects.create(
                    confirmation_id=confirmation.id,
                    client_id=client.id,
                    product_id=product_id,
                    quantity=total_quantity,
                    price=price,)


class ConfirmationDelivery(models.Model):
    confirmation = models.ForeignKey(
        Confirmation, on_delete=models.CASCADE, related_name="delivery_data")
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="delivery_data")
    quantity = models.PositiveIntegerField()
    delivery_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ("confirmation", "product", "delivery_date")

    @classmethod
    def save_confirmation_delivery(cls, confirmation_data_json, confirmation):
        filtered_data = [
            item for item in confirmation_data_json if item['product'] != "" and
            item['delivery_date'] != "" and item['delivery_date'] != "None"]
        sorted_data = sorted(filtered_data,
                             key=lambda x: (x['product'], x['delivery_date']))
        grouped = groupby(
            sorted_data,
            key=lambda x: (x['product'], x['delivery_date']))
        for (product_item, delivery_date), group in grouped:
            items = list(group)
            product, delivery = (product_item, delivery_date)
            try:
                delivery_date = datetime.fromtimestamp(
                    delivery / 1000).strftime('%Y-%m-%d')
            except Exception as e:  # pylint: disable=W0718
                delivery_date = None
            quantity = sum(int(item['quantity']) for item in items)
            cls.objects.create(
                confirmation_id=confirmation.id, product_id=product, delivery_date=delivery_date, quantity=quantity)
