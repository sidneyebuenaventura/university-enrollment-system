from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "university.core"
    label = "core"
    verbose_name = "Core"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        # Registers the drf-spectacular extensions
        from . import openapi  # noqa: F401
