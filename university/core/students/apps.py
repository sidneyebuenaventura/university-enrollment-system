from django.apps import AppConfig


class StudentsConfig(AppConfig):
    name = "university.core.students"
    label = "core_students"
    verbose_name = "Students"
    default_auto_field = "django.db.models.BigAutoField"
