from django.db import models
from django.forms.models import model_to_dict
from django.utils import timezone
from polymorphic.models import PolymorphicManager, PolymorphicModel
from rest_framework.serializers import ModelSerializer

from .utils import choices_help_text


class ChoiceFieldMixin:
    def __init__(self, **kwargs):
        choices_cls = kwargs.pop("choices_cls", None)
        if choices_cls:
            kwargs["choices"] = choices_cls.choices
            kwargs["help_text"] = choices_help_text(choices_cls)
        return super().__init__(**kwargs)


class TextChoiceField(ChoiceFieldMixin, models.CharField):
    pass


class IntegerChoiceField(ChoiceFieldMixin, models.IntegerField):
    pass


class SoftDeleteMixin:
    def soft_delete(self, commit=True):
        self.deleted_at = timezone.now()
        if commit:
            self.save()

    def restore(self):
        self.deleted_at = None
        self.save()


class BaseModelMixin:
    def to_dict(self, **kwargs):
        return model_to_dict(self, **kwargs)

    def to_json(self):
        class ProxySerializer(ModelSerializer):
            class Meta:
                model = self._meta.model
                fields = "__all__"
                depth = 1

        return ProxySerializer(self).data


class BaseModel(BaseModelMixin, models.Model):
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        abstract = True


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class SoftDeleteModel(SoftDeleteMixin, BaseModel):
    deleted_at = models.DateTimeField(
        null=True, blank=True, default=None, db_index=True
    )

    objects = models.Manager()
    active_objects = SoftDeleteManager()

    class Meta:
        abstract = True


class PolymorphicBaseModel(BaseModelMixin, PolymorphicModel):
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    objects = PolymorphicManager()

    class Meta:
        abstract = True


class PolymorphicSoftDeleteManager(PolymorphicManager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class PolymorphicSoftDeleteModel(SoftDeleteMixin, PolymorphicBaseModel):
    deleted_at = models.DateTimeField(
        null=True, blank=True, default=None, db_index=True
    )

    objects = PolymorphicManager()
    active_objects = PolymorphicSoftDeleteManager()

    class Meta:
        abstract = True
