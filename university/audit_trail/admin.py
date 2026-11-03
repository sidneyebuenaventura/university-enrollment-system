from django.contrib import admin

from .models import TrailLog


@admin.register(TrailLog)
class TrailLogAdmin(admin.ModelAdmin):
    list_display = [
        "log_id",
        "actor_name",
        "actor_type",
        "action",
        "target_ctype",
        "datetime",
    ]
    list_filter = ["actor_type", "action", "target_ctype"]
    search_fields = ["log_id", "actor_name", "target_name"]

    fieldsets = (
        (
            "Actor",
            {
                "fields": (
                    "actor_name",
                    "actor_type",
                    "actor_ctype",
                    "actor_id",
                )
            },
        ),
        (
            "Target",
            {
                "fields": (
                    "target_ctype",
                    "target_id",
                )
            },
        ),
        (
            "Information",
            {
                "fields": (
                    "action",
                    "description",
                    "meta",
                    "datetime",
                )
            },
        ),
    )

    def has_add_permission(self, *args, **kwargs):
        return False

    def has_change_permission(self, *args, **kwargs):
        return False

    def has_delete_permission(self, *args, **kwargs):
        return False
