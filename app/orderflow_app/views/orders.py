import json
import logging
from pathlib import Path

from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db import transaction
from django.contrib import messages
from django.shortcuts import redirect

from ..models.orders import Order, OrderItem
from ..forms.orders import (
    OrderModelForm,
    EditOrderModelForm,
    ViewOrderModelForm,
    ViewOrderItemFormSet,
    EditOrderItemFormSet,
)
from ..forms.uploadfile import UploadOrderForm

log = logging.getLogger(__name__)

template_path = Path("orderflow_app") / "orders"


class OrderListView(ListView):
    model = Order
    template_name = template_path/"orders.html"
    context_object_name = "orders"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "title": self.context_object_name.capitalize()
        })
        for order in context[self.context_object_name]:
            order.invoices = order.invoiced_items.select_related(
                'invoice').values('invoice__name', 'invoice__id').distinct()
        return context

    def get_queryset(self):
        return super().get_queryset().order_by("-order_date", "name")


class OrderDetailView(DetailView):
    model = Order
    model_item = OrderItem
    form_class = ViewOrderModelForm
    formset_class = ViewOrderItemFormSet
    template_name = template_path/"vieworder.html"
    context_object_name = 'vieworder'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.get_object()
        order_items = self.model_item.objects.select_related(
            'client',
            'product'
        ).filter(order=order)
        order_form = self.form_class(instance=order)
        formset = self.formset_class(queryset=order_items)
        context.update({
            'title': f'Order: {order.name}',
            'order_form': order_form,
            'formset': formset,
            'view_order': True,
        })
        return context


class OrderDeleteView(DeleteView):
    model = Order
    success_url = reverse_lazy('orders')

    def form_valid(self, form):
        if self.object.confirmations.exists():
            messages.error(
                self.request,
                f"Cannot delete order {self.object.pk}, as it has confirmations"
            )
            return redirect(self.request.META.get('HTTP_REFERER', '/'))
        messages.success(self.request, f'Order {self.object.pk} was deleted')
        return super().form_valid(form)


class OrderUpdateView(UpdateView):
    model = Order
    model_item = OrderItem
    form_class = EditOrderModelForm
    formset_class = EditOrderItemFormSet
    formset_class_not_allowed = ViewOrderItemFormSet
    template_name = template_path/"vieworder.html"
    context_object_name = 'editorder'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.get_object()
        order_items = self.model_item.objects.select_related(
            'client',
            'product'
        ).filter(order=order)
        if self.object.confirmations.exists():
            formset = self.formset_class_not_allowed(
                queryset=order_items, initial=[{'order': order}],)
        else:
            formset = self.formset_class(
                queryset=order_items, initial=[{'order': order}],)
        context.update({
            'order_form': self.get_form(),
            'formset': formset,
        })
        return context

    def get_success_url(self):
        return reverse_lazy('vieworder', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        context = self.get_context_data()
        if 'save' in self.request.POST:
            if self.object.confirmations.exists():
                order_items = self.model_item.objects.select_related(
                    'client',
                    'product'
                ).filter(order=self.get_object())
                formset = self.formset_class_not_allowed(
                    queryset=order_items)
                if form.is_valid():
                    form.save()
                    messages.success(self.request, "Order is updated")
                    return super().form_valid(form)
            else:
                formset = self.formset_class(
                    self.request.POST,
                    queryset=self.model_item.objects.filter(
                        order=self.get_object()),
                    initial=[{'order': self.get_object()}],)
                if form.is_valid() and formset.is_valid():
                    form.save()
                    formset.save(commit=False)
                    for obj in formset.deleted_objects:
                        obj.delete()
                    formset.save()
                    messages.success(
                        self.request, "Order and items are updated")
                    return super().form_valid(form)
            context.update({
                'order_form': form,
                'formset': formset,
            })
        return self.render_to_response(context)


class OrderCreateView(CreateView):
    model = Order
    model_item = OrderItem
    form_class = OrderModelForm
    loadform_class = UploadOrderForm
    template_name = template_path/"addorder.html"
    context_object_name = 'addorder'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        loadform = self.loadform_class
        context.update({
            'form': self.get_form(),
            'loadform': loadform,
            'title': 'New Order',
            'add_order_disabled': True,
        })
        return context

    def get_success_url(self):
        return reverse_lazy('orders')

    def form_valid(self, form):  # pylint: disable=R1710
        context = self.get_context_data()
        loadform = self.loadform_class(self.request.POST, self.request.FILES)
        action = self.request.POST.get('action')
        if action == 'preview':
            if uploaded_file := self.request.FILES.get('file'):
                try:
                    supplier = form.cleaned_data["supplier"]
                    order_data = loadform.load_excel_order(
                        uploaded_file, supplier=supplier)
                    self.request.session['order_data_json'] = loadform.data_json(
                        order_data)
                    context.update({
                        'orderdata': order_data,
                        'add_order_disabled': False,
                    })
                except Exception as e:  # pylint: disable=W0718
                    messages.error(
                        self.request, f'Cannot upload data from {uploaded_file}, {str(e)}')
                    context.update({
                        'add_order_disabled': True,
                    })
            else:
                messages.error(self.request, 'No file selected. Choose file')
                context.update({
                    'add_order_disabled': True,
                })
            return self.render_to_response(context)
        if action == 'add':
            if form.is_valid() and loadform.is_valid():
                order_data_json = json.loads(
                    self.request.session.get('order_data_json'))
                try:
                    with transaction.atomic():
                        order = form.save()
                        self.model_item.save_order_items(
                            order_data_json=order_data_json, order=order)
                except Exception as e:  # pylint: disable=W0718
                    messages.error(self.request, f'Cannot save data, {e}')
                    context.update({
                        'add_order_disabled': True,
                    })
                    return self.render_to_response(context)
                del self.request.session['order_data_json']
                messages.success(self.request, 'Order is created')
                return super().form_valid(form)
