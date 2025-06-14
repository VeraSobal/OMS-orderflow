from django.apps import AppConfig


class OrderflowAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'orderflow_app'

    def ready(self):

        from . import signals  # pylint: disable=W0611
