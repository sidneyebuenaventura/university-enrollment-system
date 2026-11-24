from django.apps import AppConfig


class PaymentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "university.payment"

    def ready(self):
        # Registers the drf-spectacular extensions
        from . import openapi  # noqa: F401
