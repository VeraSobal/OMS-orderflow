from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings

from .tasks import log_action


@receiver(post_save)
def log_post_save(sender, instance, created, **kwargs):
    if settings.DEBUG is False and sender.__name__.lower() in settings.MODEL_SIGNALS:
        action = "created" if created else "updated"
        log_action.delay({
            "model": sender.__name__,
            "id": instance.pk,
            "name": str(instance),
            "action": action
        })


@receiver(post_delete)
def log_post_delete(sender, instance, **kwargs):
    if settings.DEBUG is False and sender.__name__.lower() in settings.MODEL_SIGNALS:
        log_action.delay({
            "model": sender.__name__,
            "id": instance.pk,
            "name": str(instance),
            "action": "deleted"
        })
