import json
import logging
from pathlib import Path

from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db import transaction
from django.contrib import messages
from django.http import HttpResponse


from ..models.invoices import Invoice, InvoiceItem
from ..forms.invoices import (
    InvoiceModelForm,
    ViewInvoiceModelForm,
    ViewInvoiceItemFormSet,
    EditInvoiceModelForm,
    EditInvoiceItemFormSet,
)
from ..forms.uploadfile import UploadInvoiceForm

log = logging.getLogger(__name__)

template_path = Path("orderflow_app") / "invoices"


class InvoiceListView(ListView):
    model = Invoice
    template_name = template_path/"invoices.html"
    context_object_name = "invoices"

    def get_queryset(self):
        return super().get_queryset().order_by("-invoice_date", "name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "title": self.context_object_name.capitalize()
        })
        return context


class InvoiceDetailView(DetailView):
    model = Invoice
    model_item = InvoiceItem
    form_class = ViewInvoiceModelForm
    formset_class = ViewInvoiceItemFormSet
    template_name = template_path/"viewinvoice.html"
    context_object_name = 'viewinvoice'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice = self.get_object()
        invoice_items = self.model_item.objects.select_related(
            'client',
            'product'
        ).filter(
            invoice=invoice)
        invoice_form = self.form_class(instance=invoice)
        invoice_items_formset = self.formset_class(
            queryset=invoice_items,
            form_kwargs={'invoice': invoice})
        non_client_products = list(invoice_items.filter(
            client_id="Unknown").values_list('product', flat=True))
        if non_client_products:
            messages.error(
                self.request, f"Products have no client data : {', '.join(non_client_products)}")
        context.update({
            'title': f'Invoice: {invoice.name}',
            'invoice_form': invoice_form,
            'formset': invoice_items_formset,
            'view_invoice': True,
        })
        return context


class InvoiceDeleteView(DeleteView):
    model = Invoice
    success_url = reverse_lazy('invoices')

    def form_valid(self, form):
        messages.success(
            self.request, f'Invoice {self.object.pk} was deleted')
        return super().form_valid(form)


class InvoiceUpdateView(UpdateView):
    model = Invoice
    model_item = InvoiceItem
    form_class = EditInvoiceModelForm
    formset_class = EditInvoiceItemFormSet
    formset_class_not_allowed = ViewInvoiceItemFormSet
    template_name = template_path/"viewinvoice.html"
    context_object_name = 'editinvoice'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice = self.get_object()
        invoice_items = self.model_item.objects.select_related(
            'client',
            'product'
        ).filter(
            invoice=invoice)
        formset = self.formset_class(
            queryset=invoice_items, form_kwargs={'invoice': invoice},)
        context.update({
            'invoice_form': self.get_form(),
            'formset': formset,
            'view_invoice': False,
        })
        return context

    def get_success_url(self):
        return reverse_lazy('viewinvoice', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        context = self.get_context_data()
        invoice = self.get_object()
        if 'save' in self.request.POST:
            formset = self.formset_class(
                self.request.POST, form_kwargs={'invoice': invoice})
            if form.is_valid() and formset.is_valid():
                form.save()
                formset.save(commit=False)
                for obj in formset.deleted_objects:
                    obj.delete()
                formset.save()
                return super().form_valid(form)
            context.update({
                'invoice_form': form,
                'formset': formset,
                'formset_errors': formset.non_form_errors(),
            })
        return self.render_to_response(context)


class InvoiceCreateView(CreateView):
    model = Invoice
    model_item = InvoiceItem
    form_class = InvoiceModelForm
    loadform_class = UploadInvoiceForm
    template_name = template_path/"addinvoice.html"
    context_object_name = 'addinvoice'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        loadform = self.loadform_class
        context.update({
            'form': self.get_form(),
            'loadform': loadform,
            'title': 'New Invoice',
            'add_invoice_disabled': True,
        })
        return context

    def get_success_url(self):
        return reverse_lazy('viewinvoice', kwargs={'pk': self.object.pk})

    def form_valid(self, form):  # pylint: disable=R1710
        context = self.get_context_data()
        loadform = self.loadform_class(self.request.POST, self.request.FILES)
        action = self.request.POST.get('action')
        if action == 'preview':
            if uploaded_file := self.request.FILES.get('file'):
                try:
                    supplier = form.cleaned_data["supplier"]
                    invoice_id, invoice_data = loadform.load_excel_invoice(
                        uploaded_file, supplier=supplier)
                    form.instance.invoice_id = invoice_id
                    form.save(commit=False)
                    self.request.session['invoice_data_json'] = loadform.data_json(
                        invoice_data)
                    context.update({
                        'form': self.form_class(instance=form.instance),
                        'invoicedata': invoice_data,
                        'add_invoice_disabled': False,
                    })
                except Exception as e:  # pylint: disable=W0718
                    messages.error(
                        self.request, f'Cannot upload data from {uploaded_file}, {str(e)}')
                    context.update({
                        'add_invoice_disabled': True,
                    })
            else:
                messages.error(self.request, 'No file selected. Choose file')
                context.update({
                    'add_invoice_disabled': True,
                })
            return self.render_to_response(context)
        if action == 'add':
            if form.is_valid() and loadform.is_valid():
                invoice_data_json = json.loads(
                    self.request.session.get('invoice_data_json'))
                try:
                    with transaction.atomic():
                        invoice = form.save(commit=False)
                        invoice.save()
                        form.save_m2m()
                        self.model_item.save_invoice_items(
                            invoice_data_json=invoice_data_json, invoice=invoice)
                except Exception as e:  # pylint: disable=W0718
                    messages.error(self.request, f'Cannot save data, {e}')
                    context.update({
                        'add_invoice_disabled': True,
                    })
                    return self.render_to_response(context)
                del self.request.session['invoice_data_json']
                messages.success(self.request, 'Invoice is created')
                return super().form_valid(form)


def export_invoice_to_excel(request, pk):
    invoice = Invoice.objects.get(id=pk)
    invoice_items = InvoiceItem.objects.filter(
        invoice_id=pk).order_by("-client_id")
    formset = ViewInvoiceItemFormSet(queryset=invoice_items, form_kwargs={
        'invoice': invoice})
    excel_file = formset.export_to_excel()
    if excel_file:
        excel_response = HttpResponse(
            excel_file.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={
                'Content-Disposition': f'attachment; filename="data-{pk}.xlsx"'
            }
        )
        return excel_response
    return HttpResponse()
