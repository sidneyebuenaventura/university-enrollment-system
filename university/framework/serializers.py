import uuid
from typing import Union

from django.db.models import Model
from rest_framework import serializers

from .utils import choices_help_text


def _create_serializer_class(
    fields: dict, meta_model: Model, meta_fields: Union[tuple, list, str]
):
    # suffix makes the serializer unique avoiding conflict
    # when generating openapi schema
    suffix = str(uuid.uuid4()).replace("-", "")
    name = f"{meta_model.__name__}{suffix}"

    class Meta:
        model = meta_model
        fields = meta_fields

    _fields = fields.copy()
    _fields["Meta"] = Meta
    return type(name, (serializers.ModelSerializer,), _fields)


def inline_serializer_class(
    model: Model,
    fields: Union[tuple, list, str],
    declared_fields: dict = None,
    **kwargs,
):
    if not declared_fields:
        declared_fields = {}

    _declared_fields = declared_fields.copy()
    _declared_fields.update(kwargs)
    return _create_serializer_class(
        fields=_declared_fields, meta_model=model, meta_fields=fields
    )


class InlineSerializerMixin:
    # Deprecated

    def inline_serializer_class(
        self, fields: dict, meta_model: Model, meta_fields: Union[tuple, list, str]
    ):
        name = f"{type(self).__name__}{meta_model.__name__}InlineSerializer"

        class Meta:
            model = meta_model
            fields = meta_fields

        _fields = fields.copy()
        _fields["Meta"] = Meta
        serializer_class = type(name, (serializers.ModelSerializer,), _fields)

        return serializer_class

    def inline_serializer(
        self,
        model: Model = None,
        fields: dict = None,
        meta_fields: Union[tuple, list, str] = None,
        data: dict = None,
        **kwargs,
    ):
        if fields is None:
            fields = {}
        if meta_fields is None:
            meta_fields = "__all__"

        _fields = fields.copy()

        for name, field in fields.items():
            method_name = f"get_{name}"

            if (
                isinstance(field, serializers.SerializerMethodField)
                and method_name not in _fields
            ):
                _fields[method_name] = getattr(type(self), method_name)

        serializer_class = self.inline_serializer_class(
            fields=_fields, meta_model=model, meta_fields=meta_fields
        )

        if data is not None:
            return serializer_class(data=data, **kwargs)

        return serializer_class(**kwargs)


class ChoiceField(serializers.ChoiceField):
    def __init__(self, **kwargs):
        choices_cls = kwargs.pop("choices_cls", None)
        if choices_cls:
            kwargs["choices"] = choices_cls.choices
            kwargs["help_text"] = choices_help_text(choices_cls)
        return super().__init__(**kwargs)


class DryRunModelSerializer(serializers.ModelSerializer):
    dry_run = serializers.BooleanField(
        default=False, help_text="Set to true to disable saving."
    )

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        if "dry_run" not in fields:
            fields = fields + ("dry_run",)
        return fields

    def save(self, **kwargs):
        if self.validated_data.get("dry_run", False):
            return self.instance
        self.validated_data.pop("dry_run")
        return super().save(**kwargs)
