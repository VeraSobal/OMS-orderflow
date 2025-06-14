from pathlib import Path

from django.views.generic import ListView
from django.db.models import Prefetch, Window, F
from django.db.models.functions import RowNumber

from ..models.directories import Client, Supplier, Brand, Product, ProductDetail

template_path = Path("orderflow_app") / "directories"


class ClientListView(ListView):
    model = Client
    template_name = template_path/"clients.html"
    context_object_name = "clients"


class BrandListView(ListView):
    model = Brand
    template_name = template_path/"brands.html"
    context_object_name = "brands"


class SupplierListView(ListView):
    model = Supplier
    template_name = template_path/"suppliers.html"
    context_object_name = "suppliers"


class ProductListView(ListView):
    model = Product
    template_name = template_path/"products.html"
    context_object_name = "products"

    def get_queryset(self):
        return super().get_queryset().prefetch_related(
            Prefetch("details",
                     queryset=ProductDetail.objects.annotate(
                         row_num=Window(
                             expression=RowNumber(),
                             partition_by=[F("product_id"), F(
                                 "pricelist__supplier_id")],
                             order_by=[F("pricelist__starts_from").desc()]
                         )).filter(row_num=1),
                     to_attr='prefetched_details')
        ).order_by("brand", "id")
