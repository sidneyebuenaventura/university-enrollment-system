from django.apps import AppConfig


class MaintenanceConfig(AppConfig):
    name = "university.core.maintenance"
    label = "core_maintenance"
    verbose_name = "Maintenance"
    default_auto_field = "django.db.models.BigAutoField"
