from datetime import date

from django.db import models
from django.dispatch import receiver


class Client(models.Model):
    id = models.CharField(max_length=10, primary_key=True, null=False)
    name = models.CharField(max_length=100)
    comment = models.CharField(
        max_length=450, null=True, blank=True, default=None)

    def __str__(self):
        return self.name


class Supplier (models.Model):
    id = models.CharField(max_length=10, primary_key=True, null=False)
    name = models.CharField(max_length=100)
    comment = models.CharField(
        max_length=450, null=True, blank=True, default=None)
    brand = models.ManyToManyField("Brand", related_name="suppliers")

    def __str__(self):
        return f'{self.id} - {self.name}'


class Brand(models.Model):
    id = models.CharField(max_length=10, primary_key=True, null=False)
    name = models.CharField(max_length=100)
    comment = models.CharField(
        max_length=450, null=True, blank=True, default=None)

    def __str__(self):
        return f'{self.id} - {self.name}'


class Product(models.Model):
    class State(models.TextChoices):
        VALID = "Valid"
        INVALID = "Invalid"
    id = models.CharField(max_length=200, primary_key=True, null=False)
    second_id = models.CharField(max_length=200, unique=True, null=True)
    name = models.CharField(null=True, blank=True)
    description = models.CharField(null=True, blank=True)
    brand = models.ForeignKey(
        Brand, on_delete=models.CASCADE, related_name="products")
    state = models.CharField(
        max_length=50, choices=State.choices, default=State.VALID)
    comment = models.CharField(
        max_length=450, null=True, blank=True, default=None)

    def __str__(self):
        return self.id


@receiver(models.signals.pre_save, sender=Product)
def set_id(sender, instance, **kwargs):
    if not instance.id:
        code = instance.name.replace(".", "").replace(
            "-", "").replace(" ", "").upper()
        if code.isascii():
            instance.id = code+"_"+instance.brand.id


class PriceList(models.Model):
    class State(models.TextChoices):
        VALID = "Valid"
        INVALID = "Invalid"
    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, related_name="pricelists")
    pricelist_date = models.DateField(default=date.today)
    state = models.CharField(
        max_length=50, choices=State.choices, default=State.VALID)
    starts_from = models.DateField(default=date.today)
    comment = models.CharField(
        max_length=450, null=True, blank=True, default=None)

    def __str__(self):
        return f"{self.supplier.name}"


class ProductDetail(models.Model):
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="details")
    pricelist = models.ForeignKey(
        PriceList, on_delete=models.CASCADE, related_name="products")

    def __str__(self):
        return f"{self.price} - {self.pricelist.state}"
