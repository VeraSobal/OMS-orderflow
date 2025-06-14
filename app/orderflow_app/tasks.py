import sys
from pathlib import Path
from datetime import datetime

from django.core import management
from django.conf import settings
from celery import shared_task
from celery.utils.log import get_task_logger


log = get_task_logger(__name__)


@shared_task
def log_action(log_object):
    result = {
        "timestamp": datetime.now().isoformat(),
        "id": log_object.get("id"),
        "name": log_object.get("name"),
        "model": log_object.get("model"),
        "action": log_object.get("action"),
    }
    log.info(f"Got action: {result}")
    return result


def get_current_app_name():
    current_module = sys.modules[__name__]
    app_path = Path(current_module.__file__).parent
    return app_path.stem


@shared_task
def create_backup():
    app_name = get_current_app_name()
    backup_filename = settings.BACKUP_FILE(
        app_name,
        f"{app_name}-{datetime.now():%Y-%m-%d-%H-%M}"
    )
    with open(backup_filename, "w", encoding="utf-8") as f:
        management.call_command(
            "dumpdata", app_name, stdout=f, exclude=[])
    result = {
        "timestamp": datetime.now().isoformat(),
        "action": "database_backup",
    }
    log.info(f"Got action: {result}")
    return result
