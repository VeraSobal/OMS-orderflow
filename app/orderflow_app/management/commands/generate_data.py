import random

from faker import Faker
from django.core.management.base import BaseCommand

from orderflow_app.models.directories import (
    Client,
    Brand,
    Supplier,
    Product,
    ProductDetail,
    PriceList
)


class Command(BaseCommand):
    help = 'Generate test data'

    def handle(self, *args, **kwargs):

        self.stdout.write('Started generating test data')
        fake = Faker(['en_US'])
        for _ in range(3):
            Client.objects.create(
                id=fake.ean(length=8),
                name=fake.company(),
            )
            supplier = Supplier.objects.create(
                id=fake.ean(length=8),
                name=fake.company(),
            )
            brand = Brand.objects.create(
                id=fake.ean(length=8),
                name=fake.last_name(),
            )
            if random.randint(1, 10) % 2:
                supplier.brand.add(brand)
                state = "VALID"
            else:
                state = "INVALID"
            pricelist = PriceList.objects.create(
                supplier=supplier,
                pricelist_date=fake.date(),
                state=state,
            )
            for _ in range(random.randint(0, 5)):
                product = Product.objects.create(
                    name=fake.ean(length=8),
                    description=f"{fake.word()} {fake.word()}",
                    brand=brand,
                    state=state
                )
                ProductDetail.objects.create(
                    price=random.randint(10, 10000)/100,
                    product=product,
                    pricelist=pricelist
                )

        self.stdout.write('Finished test data generation ')
