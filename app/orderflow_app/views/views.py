import json
from datetime import datetime
from pathlib import Path

from django.shortcuts import render
from django.http import HttpResponse

from ..models.report import get_balance, export_to_excel

template_path = Path("orderflow_app")


def index(request):
    context = {"now": datetime.now()}
    return render(request, template_path/"index.html",  context=context)


def report(request):
    data = get_balance()
    context = {
        "title": f"Report {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}",
        "data": data,
    }
    return render(request, template_path/"report.html",  context=context)


def export_report_to_excel(request):
    json_data = request.POST.get('data').replace("'", "\"")
    data = json.loads(json_data)
    excel_file = export_to_excel(data)
    if excel_file:
        excel_response = HttpResponse(
            excel_file.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={
                'Content-Disposition': 'attachment; filename="data-report.xlsx"'
            }
        )
        return excel_response
    return HttpResponse()
