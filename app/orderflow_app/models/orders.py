from django.db import models
from django.dispatch import receiver

from .directories import Supplier, Client, Product


class Order(models.Model):
    id = models.CharField(primary_key=True, null=False, max_length=450)
    name = models.CharField(null=False, blank=False, max_length=450)
    order_date = models.DateField()
    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, related_name="orders")
    comment = models.CharField(
        max_length=450, null=True, blank=True, default=None)

    @property
    def total_quantity(self):
        return sum(item.quantity for item in self.items.all())

    class Meta:
        ordering = ['-order_date']

    @staticmethod
    def name_into_id(filename):
        filename_without_extension = ".".join(filename.split(".")[:-1])
        name_ends = "-".join(filename_without_extension.upper().replace(
            " ", "").replace(".", "").split("-")[1:])
        name_starts = filename_without_extension.split(
            '-', maxsplit=1)[0].strip()
        return "-".join([name_starts, name_ends])

    def __str__(self):
        return self.name


@receiver(models.signals.pre_save, sender=Order)
def set_id(sender, instance, **kwargs):
    if not instance.id:
        instance.id = instance.name_into_id(instance.name)


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items")
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="ordered_products")
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="ordered")
    quantity = models.PositiveIntegerField()

    class Meta:
        unique_together = ("order", "client", "product")

    @classmethod
    def save_order_items(cls, order_data_json, order):
        for item in order_data_json:
            product_id = item.get("product")
            if product_id != "total":
                second_id = item.get("second_id")
                if product_id == second_id:
                    second_id = None
                brand_id = product_id.split("_")[1]
                client_id = item.get("client")
                quantity = item.get("quantity")
                product, created = Product.objects.get_or_create(
                    id=product_id, second_id=second_id, brand_id=brand_id)
                cls.objects.create(
                    order_id=order.id,
                    client_id=client_id,
                    product_id=product_id,
                    quantity=quantity)
