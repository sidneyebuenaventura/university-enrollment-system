from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from university.framework.permissions import IsAdminUser

from . import models, serializers


class ModuleConfigurationListAPIView(ListAPIView):
    queryset = models.ModuleConfiguration.objects.filter(is_active=True)
    serializer_class = serializers.ModuleConfigurationSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]


class EnrollmentScheduleViewSet(ModelViewSet):
    queryset = models.EnrollmentSchedule.objects.all()
    serializer_class = serializers.EnrollmentScheduleSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["config"]

    http_method_names = ModelViewSet.http_method_names.copy()
    http_method_names.remove("delete")
