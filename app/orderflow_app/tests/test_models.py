from datetime import date, datetime
from decimal import Decimal

import pytest
from ..models.directories import (
    Client,
    Brand,
    Supplier,
    Product,
    ProductDetail,
    PriceList,
)
from ..models.orders import (
    Order,
    OrderItem,
)
from ..models.confirmations import (
    Confirmation,
    ConfirmationItem,
    ConfirmationDelivery,
)
from ..models.invoices import (
    Invoice,
    InvoiceItem,
)
from ..models.cancellations import (
    Cancellation,
    CancellationItem,
)


@pytest.mark.django_db
def test_client_creation(clients, amount=2):
    client0 = clients.get("0")
    assert Client.objects.count() == amount
    assert client0.id == "C0"
    assert client0.name == "Test client 0"
    assert str(client0) == "Test client 0"


@pytest.mark.django_db
def test_brand_creation(brands, amount=2):
    brand0 = brands.get("0")
    assert Brand.objects.count() == amount
    assert brand0.id == "B0"
    assert brand0.name == "Test brand B0"
    assert str(brand0) == "B0 - Test brand B0"


@pytest.mark.django_db
def test_supplier_creation(supplier, brands):
    assert Supplier.objects.count() == 1
    assert supplier.id == "T00016"
    assert supplier.name == "Test supplier 0"
    assert str(supplier) == "T00016 - Test supplier 0"
    assert supplier.brand.all().count() == 2
    assert brands.get("0").suppliers.all().count() == 1


@pytest.mark.django_db
def test_product_creation(products, brands, amount=4):
    product0 = products.get("0")
    assert Product.objects.count() == amount
    assert product0.id == "TESTPRODUCT0_B0"
    assert product0.name == "Test product 0"
    assert product0.brand == brands.get("0")
    assert str(product0) == "TESTPRODUCT0_B0"


@pytest.mark.django_db
def test_pricelist_creation(pricelist, supplier):
    assert PriceList.objects.count() == 1
    assert pricelist.supplier == supplier
    assert pricelist.state == "Valid"
    assert pricelist.pricelist_date == date.today()
    assert pricelist.starts_from == date.today()


@pytest.mark.django_db
def test_productdetail_creation(productdetail, products, pricelist):
    assert ProductDetail.objects.count() == 1
    assert productdetail.pricelist == pricelist
    assert productdetail.price == 1.01
    assert productdetail.product == products.get("0")
    assert str(productdetail) == "1.01 - Valid"


@pytest.mark.django_db
def test_order_creation(orders, supplier):
    order0 = orders.get("0")
    assert Order.objects.count() == 3
    new_item = Order.objects.first()
    assert order0.id == new_item.id
    assert order0.name == new_item.name
    assert order0.supplier == new_item.supplier
    assert datetime.strptime(order0.order_date,
                             '%Y-%m-%d').date() == new_item.order_date
    assert str(order0) == "Order 0-C0 -B0-S0-01-01-2025.xlsx"


@pytest.mark.django_db
def test_orderitem_creation(orderitems, amount=5):
    orderitem0 = orderitems.get("0")
    assert OrderItem.objects.count() == amount
    new_item = OrderItem.objects.first()
    assert orderitem0.order == new_item.order
    assert orderitem0.client == new_item.client
    assert orderitem0.product == new_item.product
    assert orderitem0.order.items.count() == 2
    assert orderitem0.order.total_quantity == 30


@pytest.mark.django_db
def test_confirmation_creation(confirmations):
    confirmation0 = confirmations.get("0")
    assert Confirmation.objects.count() == 2
    new_item = Confirmation.objects.first()
    assert confirmation0.id == new_item.id
    assert confirmation0.confirmation_code == new_item.confirmation_code
    assert confirmation0.name == new_item.name
    assert confirmation0.supplier == new_item.supplier
    assert datetime.strptime(confirmation0.confirmation_date,
                             '%Y-%m-%d').date() == new_item.confirmation_date
    assert confirmation0.order.all().count() == new_item.order.all().count()
    assert list(confirmation0.order.all()) == list(new_item.order.all())


@pytest.mark.django_db
def test_confirmationitem_creation(confirmationitems, amount=4):
    confirmationitem0 = confirmationitems.get("0")
    assert ConfirmationItem.objects.count() == amount
    new_item = ConfirmationItem.objects.first()
    assert confirmationitem0.confirmation == new_item.confirmation
    assert confirmationitem0.client == new_item.client
    assert confirmationitem0.product == new_item.product
    assert confirmationitem0.quantity == new_item.quantity
    assert confirmationitem0.confirmation.items.count() == 2
    assert confirmationitem0.confirmation.total_amount == Decimal("203.00")


@pytest.mark.django_db
def test_confirmationdelivery_creation(confirmationdelivery, amount=3):
    confirmationdelivery0 = confirmationdelivery.get("0")
    assert ConfirmationDelivery.objects.count() == amount
    new_item = ConfirmationDelivery.objects.first()
    assert confirmationdelivery0.confirmation == new_item.confirmation
    assert datetime.strptime(confirmationdelivery0.delivery_date,
                             '%Y-%m-%d').date() == new_item.delivery_date
    assert confirmationdelivery0.quantity == new_item.quantity
    assert confirmationdelivery0.product == new_item.product
    assert confirmationdelivery0.confirmation.delivery_data.count() == 2


@pytest.mark.django_db
def test_invoice_creation(invoices, amount=2):
    invoice0 = invoices.get("0")
    new_item = Invoice.objects.first()
    assert Invoice.objects.count() == amount
    assert invoice0.id == new_item.id
    assert invoice0.name == new_item.name
    assert invoice0.supplier == new_item.supplier
    assert datetime.strptime(invoice0.invoice_date,
                             '%Y-%m-%d').date() == new_item.invoice_date


@pytest.mark.django_db
def test_invoiceitem_creation(invoiceitems, invoices, clients, products, amount=2):
    invoiceitem0 = invoiceitems.get("0")
    assert InvoiceItem.objects.count() == amount
    new_item = InvoiceItem.objects.first()
    assert invoiceitem0.invoice == new_item.invoice
    assert invoiceitem0.client == new_item.client
    assert invoiceitem0.product == new_item.product
    assert invoiceitem0.quantity == new_item.quantity
    assert invoiceitem0.invoice.items.count() == 2
    assert invoiceitem0.invoice.total_amount == Decimal("203.00")


@pytest.mark.django_db
def test_cancellation_creation(cancellation):
    assert Cancellation.objects.count() == 1
    new_item = Cancellation.objects.first()
    assert cancellation.supplier == new_item.supplier
    assert cancellation.brand == new_item.brand
    assert datetime.strptime(cancellation.cancellation_date,
                             '%Y-%m-%d').date() == new_item.cancellation_date


@pytest.mark.django_db
def test_cancellationitem_creation(cancellationitem):
    assert CancellationItem.objects.count() == 1
    new_item = CancellationItem.objects.first()
    assert cancellationitem.cancellation == new_item.cancellation
    assert cancellationitem.client == new_item.client
    assert cancellationitem.confirmation == new_item.confirmation
    assert cancellationitem.order == new_item.order
    assert cancellationitem.product == new_item.product
    assert cancellationitem.quantity == new_item.quantity
