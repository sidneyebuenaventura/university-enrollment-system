from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from hashids import Hashids

from university.framework.models import BaseModel, TextChoiceField


class TrailLog(BaseModel):
    class Actions(models.TextChoices):
        GENERIC = "G", "Generic"
        CREATED = "C", "Created"
        UPDATED = "U", "Updated"
        DELETED = "D", "Deleted"

    HASHIDS = Hashids(
        settings.HASHIDS_TRAILLOG_SALT,
        min_length=settings.HASHIDS_MIN_LENGTH,
        alphabet=settings.HASHIDS_ALPHABET_ALPHA_ONLY,
    )

    log_id = models.CharField(max_length=255, null=True)

    actor_name = models.CharField(max_length=255, blank=True, null=True)
    actor_type = models.CharField(max_length=255, blank=True, null=True)
    actor_ctype = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="actor_logs",
    )
    actor_id = models.PositiveIntegerField(blank=True, null=True)
    actor = GenericForeignKey("actor_ctype", "actor_id")

    target_ctype = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="target_logs",
    )
    target_id = models.PositiveIntegerField(blank=True, null=True)
    target = GenericForeignKey("target_ctype", "target_id")

    action = TextChoiceField(max_length=2, choices_cls=Actions)
    description = models.TextField(blank=True)

    meta = models.JSONField(blank=True, default=dict)
    datetime = models.DateTimeField()

    def __str__(self):
        return f"Log {self.log_id}"

    def generate_log_id(self):
        self.log_id = self.HASHIDS.encode(self.id)
        self.save()
