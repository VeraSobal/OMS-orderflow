import logging

import pandas as pd
from django import forms
from django.core.exceptions import ValidationError

from ..models.directories import (
    Brand,
)

log = logging.getLogger(__name__)


class UploadFileForm(forms.Form):
    file = forms.FileField(label="", required=False, widget=forms.ClearableFileInput(attrs={
        'accept': '.xls,.xlsx',
        'multiple': False
    }))

    @staticmethod
    def data_json(data):
        return data.to_json(orient='records')

    @staticmethod
    def find_next_value(df, target_value):
        for column in df.columns.values:
            if df[column].str.contains(target_value).any():
                idx = df[column].str.contains(target_value).idxmax()
                next_col = df.columns[df.columns.get_loc(column) + 1]
                return df.loc[idx, next_col]
        return None


class UploadOrderForm(UploadFileForm):

    @staticmethod
    def __load_excel_order_T00016(uploaded_file):
        brand = uploaded_file.name.split(
            "-")[2].replace(".", "").replace(" ", "").upper()
        client = uploaded_file.name.split(
            "-")[1].replace(".", "").replace(" ", "").upper()
        df = pd.read_excel(uploaded_file, parse_dates=True, dtype=str,)
        df.columns = df.columns.str.lower()
        df.dropna(inplace=True)
        if "note" not in df.columns.values:
            df["client"] = client
        else:
            df["client"] = df["note"].apply(
                lambda x: f'{x.replace(".", "").upper()}')
        df.rename(columns={df.columns.values[0]: 'product'}, inplace=True)
        df['product'] = df['product'].astype(
            str).str.replace(".", "") + f"_{brand}"
        if df.columns.get_loc('quantity') == 2:
            df.rename(
                columns={df.columns.values[1]: 'second_id'}, inplace=True)
            df["second_id"] = df["second_id"].astype(
                str).str.replace(".", "") + f"_{brand}"
        else:
            df["second_id"] = df["product"]
        df['quantity'] = pd.to_numeric(df['quantity'])
        if brand == "B05":
            df['product'] = df['product'].str.zfill(14)
        df = df.groupby(["product", "second_id", "client", ])[
            "quantity"].sum()
        df.loc['total'] = df.sum()
        df = df.reset_index()
        df = df[['product', "second_id", 'client', 'quantity',]]
        return df

    @staticmethod
    def load_excel_order(uploaded_file, supplier):
        if supplier.id == "T00016":
            order_data = UploadOrderForm.__load_excel_order_T00016(
                uploaded_file)
        else:
            order_data = None
        return order_data


class UploadConfirmationForm(UploadFileForm):

    @staticmethod
    def __load_excel_confirmation_T00016(uploaded_file):
        brand = uploaded_file.name.split(" ")[1]
        brand_id = Brand.objects.filter(
            name__icontains=brand).first().id
        if brand_id is None:
            raise ValidationError(f"Brand {brand_id} must be in Brands")
        df = pd.read_excel(uploaded_file, parse_dates=True, dtype={},)
        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
        confirmation_code = UploadFileForm.find_next_value(
            df, 'Ihre Bestellnummer:')
        start_str = 'Pos'
        start_index = df.loc[df['Unnamed: 0'] == start_str].index[0]
        end_index = df['Unnamed: 0'].iloc[start_index:].isna().idxmax()
        if end_index == start_index:
            end_index = len(df)
        df = df.iloc[start_index: end_index].reset_index(
            drop=True)
        df.columns = df.iloc[0]
        df = df.drop(index=[0]).reset_index(drop=True).drop('Pos', axis=1)
        df.index = df.index + 1
        df['Teilenummer'] = df['Teilenummer'].astype(
            str).str.replace(".", "") + f"_{brand_id}"
        df.rename(columns={'Teilenummer': 'product'}, inplace=True)
        df.rename(columns={'Bezeichnung': 'product_name'}, inplace=True)
        df.rename(columns={'Menge': 'quantity'}, inplace=True)
        df.rename(columns={'Preise': 'price'}, inplace=True)
        df.rename(columns={'Liefertermin': 'delivery_date'}, inplace=True)
        df.rename(columns={'Betrag': 'total_price'}, inplace=True)
        df.loc['total', 'total_price'] = df['total_price'].sum()
        df = df.fillna('').replace('unknown', "").infer_objects(copy=False)
        df = df[['product', 'product_name', 'quantity',
                 'price', 'delivery_date', 'total_price']]
        return confirmation_code, df

    @staticmethod
    def load_excel_confirmation(uploaded_file, supplier):
        if supplier.id == "T00016":
            confirmation_code, confirmation_data = UploadConfirmationForm.__load_excel_confirmation_T00016(
                uploaded_file)
        else:
            confirmation_code = None
            confirmation_data = None
        return confirmation_code, confirmation_data


class UploadInvoiceForm(UploadFileForm):

    @staticmethod
    def __get_brand_id(brand_name):
        try:
            brand = Brand.objects.filter(name__icontains=brand_name).first()
            return brand.id if brand else None
        except ValidationError as e:
            raise ValidationError(
                f"Brand {brand_name} must be in Brands"
            ) from e

    @staticmethod
    def __get_product_id(product, brand_id):
        if brand_id == "B05":
            product = product.zfill(14)
        return f"{product}_{brand_id}"

    @staticmethod
    def __load_excel_invoice_T00016(uploaded_file):
        df = pd.read_excel(uploaded_file, parse_dates=True, dtype={},)
        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
        invoice_id = UploadFileForm.find_next_value(df, 'Rechnungsnummer:')
        start_str = 'Pos.'
        start_index = df.loc[df['Unnamed: 0'] == start_str].index[0]
        end_index = df['Unnamed: 0'].iloc[start_index:].isna().idxmax()
        if end_index == start_index:
            end_index = len(df)
        df = df.iloc[start_index: end_index].reset_index(
            drop=True)
        df.columns = df.iloc[0]
        df = df.drop(index=[0]).reset_index(drop=True).drop('Pos.', axis=1)
        df.index = df.index + 1
        df['Artikel'] = df['Artikel'].astype(
            str).str.replace(".", "")
        df.rename(columns={'Artikel': 'product'}, inplace=True)
        df.rename(columns={'Handelsmarke': 'brand'}, inplace=True)

        df["brand"] = df["brand"].apply(
            UploadInvoiceForm.__get_brand_id)
        df['product'] = df.apply(
            lambda x: UploadInvoiceForm.__get_product_id(x['product'], x['brand']), axis=1)
        df.rename(columns={'Artikelbezeichnung': 'product_name'}, inplace=True)
        df.rename(columns={'Menge': 'quantity'}, inplace=True)
        df.rename(columns={'Preis, EUR': 'price'}, inplace=True)
        df.rename(columns={'Betrag, EUR': 'total_price'}, inplace=True)
        df.loc['total', 'total_price'] = df['total_price'].sum()
        df = df.fillna('').replace('unknown', "").infer_objects(copy=False)

        df = df[['product', 'product_name',
                 'quantity', 'price', 'total_price',]]
        return invoice_id, df

    @staticmethod
    def load_excel_invoice(uploaded_file, supplier):
        if supplier.id == "T00016":
            invoice_id, invoice_data = UploadInvoiceForm.__load_excel_invoice_T00016(
                uploaded_file)
        else:
            invoice_id = None
            invoice_data = None
        return invoice_id, invoice_data
