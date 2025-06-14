import logging
import json

import pytest
from django.urls import reverse

log = logging.getLogger(__name__)


@pytest.mark.django_db
def test_report_view(client, confirmationitems):
    url = reverse('report')
    response = client.get(url)
    assert response.status_code == 200
    for confirmationitem in confirmationitems.values():
        assert confirmationitem.confirmation.name.encode() in response.content
        assert confirmationitem.order.name.encode() in response.content
        assert confirmationitem.client.id.encode() in response.content
        assert confirmationitem.product.id.encode() in response.content
    data = response.context['data']
    url = reverse('exportreporttoexcel')
    response = client.post(url, {'data': json.dumps(data)})
    assert response.status_code == 200
    assert 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in response['Content-Type']
    assert 'attachment; filename="data-report.xlsx"' in response['Content-Disposition']


@pytest.mark.django_db
def test_index_view(client):
    url = reverse('index')
    response = client.get(url)
    assert response.status_code == 200
