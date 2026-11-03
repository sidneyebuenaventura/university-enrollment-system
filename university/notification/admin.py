from django.contrib import admin
from polymorphic.admin import (
    PolymorphicChildModelAdmin,
    PolymorphicChildModelFilter,
    PolymorphicParentModelAdmin,
    StackedPolymorphicInline,
)

from . import models


@admin.register(models.Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["message_key"]
    raw_id_fields = ("recipients",)


class NotificationChannelInline(StackedPolymorphicInline):
    class EmailChannelInline(StackedPolymorphicInline.Child):
        model = models.EmailChannel

    model = models.NotificationChannel
    child_inlines = (EmailChannelInline,)


@admin.register(models.NotificationChannel)
class NotificationChannelParentAdmin(PolymorphicParentModelAdmin):
    list_display = ["polymorphic_ctype", "is_active"]
    child_models = (models.EmailChannel,)
    list_filter = (PolymorphicChildModelFilter,)


class NotificationChannelChildAdmin(PolymorphicChildModelAdmin):
    base_model = models.NotificationChannel


@admin.register(models.EmailChannel)
class EmailChannelAdmin(NotificationChannelChildAdmin):
    pass
