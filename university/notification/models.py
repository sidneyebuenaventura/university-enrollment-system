from django.contrib.auth import get_user_model
from django.db import models

from university.framework.models import BaseModel, PolymorphicBaseModel

User = get_user_model()


class Notification(BaseModel):
    recipients = models.ManyToManyField(User)
    message_key = models.CharField(max_length=255)
    context = models.JSONField(blank=True, default=dict)

    def __str__(self):
        return f"{self.message_key}"


class NotificationChannel(PolymorphicBaseModel):
    def get_handler(self):
        raise NotImplementedError


class EmailChannel(NotificationChannel):
    host = models.CharField(max_length=255, default="localhost")
    user = models.CharField(max_length=255, blank=True, null=True)
    password = models.CharField(max_length=255, blank=True, null=True)
    port = models.IntegerField(default=1025)
    use_tls = models.BooleanField(default=False)
    use_ssl = models.BooleanField(default=False)
    default_from = models.CharField(max_length=255, default="university@localhost")

    enable_whitelist = models.BooleanField(default=False)

    def __str__(self):
        return self.host

    def get_handler(self):
        from .services import email_handler

        return email_handler
