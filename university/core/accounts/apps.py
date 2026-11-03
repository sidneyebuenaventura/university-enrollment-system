from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "university.core.accounts"
    label = "core_accounts"
    verbose_name = "Accounts"
    default_auto_field = "django.db.models.BigAutoField"
