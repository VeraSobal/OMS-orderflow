import json
import logging
from pathlib import Path

from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db import transaction
from django.http import HttpResponse
from django.contrib import messages
from django.shortcuts import redirect
from django.db.models import F

from ..models.confirmations import Confirmation, ConfirmationItem, ConfirmationDelivery
from ..forms.confirmations import (
    ConfirmationModelForm,
    EditConfirmationModelForm,
    ViewConfirmationModelForm,
    ViewConfirmationItemFormSet,
    EditConfirmationItemFormSet)
from ..forms.uploadfile import UploadConfirmationForm

log = logging.getLogger(__name__)

template_path = Path("orderflow_app") / "confirmations"


class ConfirmationListView(ListView):
    model = Confirmation
    template_name = template_path/"confirmations.html"
    context_object_name = "confirmations"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "title": self.context_object_name.capitalize()
        })
        for confirmation in context[self.context_object_name]:
            confirmation.invoices = confirmation.invoiced_items.select_related(
                'invoice').values('invoice__name', 'invoice__id').distinct()
        return context

    def get_queryset(self):
        return super().get_queryset().order_by("-confirmation_date", "name")


class ConfirmationDetailView(DetailView):
    model = Confirmation
    model_item = ConfirmationItem
    form_class = ViewConfirmationModelForm
    formset_class = ViewConfirmationItemFormSet
    template_name = template_path/"viewconfirmation.html"
    context_object_name = 'viewconfirmation'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        confirmation = self.get_object()
        confirmation_items = self.model_item.objects.select_related(
            'client',
            'product'
        ).filter(
            confirmation=confirmation)
        confirmation_form = self.form_class(instance=confirmation)
        confirmation_items_formset = self.formset_class(
            queryset=confirmation_items,
            form_kwargs={'confirmation': confirmation})
        non_client_products = list(confirmation_items.filter(
            client_id="Unknown").values_list('product', flat=True))
        if non_client_products:
            messages.error(
                self.request, f"Products have no client data : {', '.join(non_client_products)}")
        context.update({
            'title': f'Confirmation: {confirmation.name}',
            'confirmation_form': confirmation_form,
            'formset': confirmation_items_formset,
            'view_confirmation': True,
        })
        return context


class ConfirmationDeleteView(DeleteView):
    model = Confirmation
    success_url = reverse_lazy('confirmations')

    def form_valid(self, form):
        if self.object.invoiced_items.exists():
            messages.error(
                self.request,
                f"Cannot delete confirmation {self.object.pk} as it has invoices."
            )
            return redirect(self.request.META.get('HTTP_REFERER', '/'))
        messages.success(
            self.request, f'Confirmation {self.object.pk} was deleted')
        return super().form_valid(form)


class ConfirmationUpdateView(UpdateView):
    model = Confirmation
    model_item = ConfirmationItem
    form_class = EditConfirmationModelForm
    formset_class = EditConfirmationItemFormSet
    formset_class_not_allowed = ViewConfirmationItemFormSet
    template_name = template_path/"viewconfirmation.html"
    context_object_name = 'editconfirmation'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        confirmation = self.get_object()
        confirmation_items = self.model_item.objects.select_related(
            'client',
            'product'
        ).filter(
            confirmation=confirmation)
        formset = self.formset_class(
            queryset=confirmation_items, form_kwargs={'confirmation': confirmation},)
        context.update({
            'confirmation_form': self.get_form(),
            'formset': formset,
            'view_confirmation': False,
        })
        return context

    def get_success_url(self):
        return reverse_lazy('viewconfirmation', kwargs={'pk': self.object.pk})

    def order_has_changed(self, form):
        order = form.cleaned_data["order"]
        initial_order = self.get_object().order.all()
        if len(order) == len(initial_order):
            for item in order:
                if item not in initial_order:
                    return True
            return False
        return True

    def apply_new_order(self, confirmation):
        confirmation_data_json = list(confirmation.items.annotate(
            product_name=F('product__name')
        ).values(
            'product',
            'quantity',
            'price',
            'product_name'
        ))
        confirmation.items.all().delete()
        self.model_item.save_confirmation_items(
            confirmation_data_json, confirmation)

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        confirmation = self.get_object()
        if confirmation.invoiced_items.exists():
            messages.error(
                self.request,
                f"Cannot edit confirmation {self.object.pk} as it has invoices."
            )
            return redirect(self.get_success_url())
        return response

    def form_valid(self, form):
        context = self.get_context_data()
        confirmation = self.get_object()
        if 'save' in self.request.POST:
            formset = self.formset_class(
                self.request.POST, form_kwargs={'confirmation': confirmation})
            if form.is_valid() and formset.is_valid():
                order_has_changed = self.order_has_changed(form)
                form.save()
                if order_has_changed:
                    self.apply_new_order(confirmation)
                    messages.warning(
                        self.request, 'New order has been applied to set clients')
                    return super().form_valid(form)
                formset.save(commit=False)
                for obj in formset.deleted_objects:
                    obj.delete()
                formset.save()
                return super().form_valid(form)
            context.update({
                'conformation_form': form,
                'formset': formset,
                'formset_errors': formset.non_form_errors(),
            })
        return self.render_to_response(context)


class ConfirmationCreateView(CreateView):
    model = Confirmation
    model_item = ConfirmationItem
    model_delivery = ConfirmationDelivery
    form_class = ConfirmationModelForm
    loadform_class = UploadConfirmationForm
    template_name = template_path/"addconfirmation.html"
    context_object_name = 'addconfirmation'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        loadform = self.loadform_class
        context.update({
            'form': self.get_form(),
            'loadform': loadform,
            'title': 'New Confirmation',
            'add_confirmation_disabled': True,
        })
        return context

    def get_success_url(self):
        return reverse_lazy('viewconfirmation', kwargs={'pk': self.object.pk})

    def form_valid(self, form):  # pylint: disable=R1710
        context = self.get_context_data()
        loadform = self.loadform_class(self.request.POST, self.request.FILES)
        action = self.request.POST.get('action')
        if action == 'preview':
            if uploaded_file := self.request.FILES.get('file'):
                try:
                    supplier = form.cleaned_data["supplier"]
                    confirmation_code, confirmation_data = loadform.load_excel_confirmation(
                        uploaded_file, supplier=supplier)
                    current_values = {
                        'order': self.request.POST.getlist('order'),
                    }
                    form.instance.confirmation_code = confirmation_code
                    form.save(commit=False)
                    self.request.session['confirmation_data_json'] = loadform.data_json(
                        confirmation_data)
                    context.update({
                        'form': self.form_class(instance=form.instance, initial=current_values),
                        'confirmationdata': confirmation_data,
                        'add_confirmation_disabled': False,
                    })
                except Exception as e:  # pylint: disable=W0718
                    messages.error(
                        self.request, f'Cannot upload data from {uploaded_file}, {str(e)}')
                    context.update({
                        'add_conformation_disabled': True,
                    })
            else:
                messages.error(self.request, 'No file selected. Choose file')
                context.update({
                    'add_confirmation_disabled': True,
                })
            return self.render_to_response(context)
        if action == 'add':
            if form.is_valid() and loadform.is_valid():
                confirmation_data_json = json.loads(
                    self.request.session.get('confirmation_data_json'))
                try:
                    with transaction.atomic():
                        confirmation = form.save(commit=False)
                        confirmation.save()
                        form.save_m2m()
                        self.model_item.save_confirmation_items(
                            confirmation_data_json=confirmation_data_json, confirmation=confirmation)
                        self.model_delivery.save_confirmation_delivery(
                            confirmation_data_json=confirmation_data_json, confirmation=confirmation)
                except Exception as e:  # pylint: disable=W0718
                    messages.error(self.request, f'Cannot save data, {e}')
                    context.update({
                        'add_confirmation_disabled': True,
                    })
                    return self.render_to_response(context)
                del self.request.session['confirmation_data_json']
                messages.success(self.request, 'Confirmation is created')
                return super().form_valid(form)


def export_confirmation_to_excel(request, pk):
    confirmation = Confirmation.objects.get(id=pk)
    confirmation_items = ConfirmationItem.objects.filter(
        confirmation_id=pk).order_by("-client_id")
    formset = ViewConfirmationItemFormSet(queryset=confirmation_items, form_kwargs={
        'confirmation': confirmation})
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
