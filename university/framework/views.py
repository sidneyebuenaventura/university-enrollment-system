from django.apps import apps
from django.conf import settings
from django.db.models import TextChoices
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import mixins, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet


class ListRetrieveViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet
):
    """
    A viewset that provides `retrieve`, `create`, and `list` actions.

    To use it, override the class and set the `.queryset` and
    `.serializer_class` attributes.
    """


class ListRetrieveUpdateViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    """
    A viewset that provides `retrieve`, `update`, and `list` actions.

    To use it, override the class and set the `.queryset` and
    `.serializer_class` attributes.
    """


class ApiSerializerClassMixin:
    def get_serializer_class(self):
        method = self.request.method.lower()
        return self.serializer_classes.get(method, self.serializer_class)


class ViewSetSerializerClassMixin:
    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.serializer_class)


class DryRunModelViewSet(ModelViewSet):
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        headers = self.get_success_headers(serializer.data)

        if serializer.data.get("dry_run", False):
            return Response({"dry_run": True}, headers=headers)

        serializer.validated_data.pop("dry_run", None)
        self.perform_create(serializer)

        output_serializer = self.get_serializer(instance=serializer.instance)
        return Response(
            output_serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data.get("dry_run", False):
            return Response({"dry_run": True}, status=status.HTTP_200_OK)

        serializer.validated_data.pop("dry_run", None)
        self.perform_update(serializer)

        if getattr(instance, "_prefetched_objects_cache", None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)


class PermissionRequiredMixin:
    def check_permissions(self, request):
        if self.request.user.is_authenticated:
            if hasattr(self, "permissions"):
                has_all_perm = all(
                    perm in self.request.user.permissions
                    for perm in self.permissions.get(self.action, self.permission)
                )
            else:
                has_all_perm = all(
                    perm in self.request.user.permissions for perm in self.permission
                )
            if not has_all_perm:
                self.permission_denied(request)

        return super().check_permissions(request)


class ObjectPermissionRequiredMixin:
    def check_object_permissions(self, request, obj):
        if self.request.user.is_authenticated:
            has_all_perm = all(
                perm in self.request.user.permissions for perm in self.permission
            )
            if not has_all_perm:
                self.permission_denied(request)

        return super().check_permissions(request)


class HealthCheckApi(APIView):
    def get(self, request):
        return Response()


class EnumListApi(APIView):
    """Enums List

    Return dictionaries of enum choices used across every API.
    """

    permission_classes = [IsAuthenticated]

    @method_decorator(cache_page(60 * 60 * 24))  # 24 Hours
    def get(self, request, *args, **kwargs):
        enums = {}
        app_labels = []

        # Get installed service app labels
        for app_label, app_config in apps.app_configs.items():
            if app_config.name not in settings.SERVICE_APPS:
                continue

            app_labels.append(app_label)

            # Get Textchoices defined on top-level models.py
            for prop in dir(app_config.models_module):
                field = getattr(app_config.models_module, prop)

                if field.__class__ == TextChoices.__class__:
                    dict_choices = dict(field.choices)
                    enums[f"{field.__name__}"] = dict_choices

        # Get TextChoices defined on a model
        for app_label in app_labels:
            app_models = apps.all_models[app_label]

            for _, model in app_models.items():
                # Implicit Many-to-many intermediate models created by
                # Django are using snake-case format.
                if "_" in model.__name__:
                    continue

                for prop in dir(model):
                    field = getattr(model, prop)

                    if field.__class__ == TextChoices.__class__:
                        dict_choices = dict(field.choices)
                        enums[f"{model.__name__}.{field.__name__}"] = dict_choices

        return Response(enums)
