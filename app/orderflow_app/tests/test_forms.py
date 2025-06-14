from json import loads
from datetime import datetime

import pytest
from ..forms.uploadfile import (
    UploadOrderForm,
    UploadConfirmationForm,
    UploadInvoiceForm,
)


@pytest.mark.django_db
def test_uploadorderform(order_excel, supplier):
    uploadorderform = UploadOrderForm()
    uploadorderform.files = {'file': order_excel}
    order_data = uploadorderform.load_excel_order(
        order_excel, supplier=supplier)
    order_data_json = uploadorderform.data_json(order_data)
    order_data_json_expected = [
        {"product": "P0_B0", "second_id": "P0_B0", "client": "C0", "quantity": 10},
        {"product": "P1_B0", "second_id": "P1_B0", "client": "C1", "quantity": 20},
        {"product": "total", "second_id": "", "client": "", "quantity": 30},
    ]
    assert order_data_json_expected == loads(order_data_json)


@pytest.mark.django_db
def test_uploadconfirmationform(confirmation_excel, supplier):
    uploadconfirmationform = UploadConfirmationForm()
    uploadconfirmationform.files = {'file': confirmation_excel}
    confirmation_code, confirmation_data = uploadconfirmationform.load_excel_confirmation(
        confirmation_excel, supplier=supplier)
    confirmation_data_json = uploadconfirmationform.data_json(
        confirmation_data)
    confirmation_data_json_expected = [
        {'product': 'TESTPRODUCT0_B0', 'product_name': 'Test product 0', 'quantity': 10, 'price': 10.1,
            'delivery_date': int(datetime.strptime('01.01.2026', '%d.%m.%Y').timestamp()*1000), 'total_price': 101.0},
        {'product': 'TESTPRODUCT1_B0', 'product_name': 'Test product 1', 'quantity': 20, 'price': 20.02,
            'delivery_date': '', 'total_price': 400.4},
        {'product': '', 'product_name': '', 'quantity': '', 'price': '',
            'delivery_date': '', 'total_price': 501.4},
    ]
    assert confirmation_data_json_expected == loads(confirmation_data_json)
    assert confirmation_code == "T3"


@pytest.mark.django_db
def test_uploadinvoiceform(invoice_excel, supplier):
    uploadinvoiceform = UploadInvoiceForm()
    uploadinvoiceform.files = {'file': invoice_excel}
    invoice_code, invoice_data = uploadinvoiceform.load_excel_invoice(
        invoice_excel, supplier=supplier)
    invoice_data_json = uploadinvoiceform.data_json(
        invoice_data)
    invoice_data_json_expected = [
        {'product': 'TESTPRODUCT0_B0', 'product_name': 'Test product 0', 'quantity': 10,
            'price': 10.1, 'total_price': 101.0},
        {'product': 'TESTPRODUCT1_B0', 'product_name': 'Test product 1', 'quantity': 20,
            'price': 20.02, 'total_price': 400.4},
        {'product': '', 'product_name': '', 'quantity': '', 'price': '', 'total_price': 501.4},]
    assert invoice_data_json_expected == loads(invoice_data_json)
    assert invoice_code == "Invoice01"
