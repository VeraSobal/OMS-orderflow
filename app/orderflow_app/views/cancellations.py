import logging
from pathlib import Path

from django.views.generic import ListView, CreateView, DeleteView
from django.urls import reverse_lazy
from django.db import transaction
from django.contrib import messages

from ..models.cancellations import Cancellation, CancellationItem
from ..forms.cancellations import (
    CancellationModelForm,
)

log = logging.getLogger(__name__)

template_path = Path("orderflow_app") / "cancellations"


class CancellationListView(ListView):
    model = Cancellation
    template_name = template_path/"cancellations.html"
    context_object_name = "cancellations"

    def get_queryset(self):
        return super().get_queryset().order_by("-cancellation_date", "brand", "supplier")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "title": self.context_object_name.capitalize()
        })
        return context


class CancellationDeleteView(DeleteView):
    model = Cancellation
    success_url = reverse_lazy('cancellations')

    def form_valid(self, form):
        messages.success(
            self.request, f'Cancellation {self.object.cancellation_date}|-| {self.object.brand.name} |-| {self.object.supplier.name} was deleted')
        return super().form_valid(form)


class CancellationCreateView(CreateView):
    model = Cancellation
    model_item = CancellationItem
    form_class = CancellationModelForm
    template_name = template_path/"addcancellation.html"
    context_object_name = 'addcancellation'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'form': self.get_form(),
            'title': 'New Cancellation',
            'preview_hidden': True,
            'add_confirmation_disabled': False,
        })
        return context

    def get_success_url(self):
        return reverse_lazy('cancellations')

    def form_valid(self, form):  # pylint: disable=R1710
        context = self.get_context_data()
        action = self.request.POST.get('action')
        if action == 'add':
            if form.is_valid():
                cancellation_data = form.cleaned_data["cancellation_data"]
                try:
                    with transaction.atomic():
                        cancellation = form.save(commit=False)
                        cancellation.save()
                        form.save_m2m()
                        self.model_item.save_cancellation_items(
                            cancellation_data=cancellation_data, cancellation=cancellation)
                except Exception as e:  # pylint: disable=W0718
                    messages.error(self.request, f'Cannot save data, {e}')
                    return self.render_to_response(context)
                messages.success(self.request, 'Cancellation is applied')
                return super().form_valid(form)
