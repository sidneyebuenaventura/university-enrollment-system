from rest_framework import serializers

from university.core.accounts.serializers import ModuleSerializer
from university.framework.utils import choices_help_text

from . import models


class ModuleConfigurationSerializer(serializers.ModelSerializer):
    module = ModuleSerializer()

    class Meta:
        model = models.ModuleConfiguration
        exclude = ("is_active",)


class EnrollmentScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.EnrollmentSchedule
        fields = (
            "id",
            "config",
            "status",
            "start_datetime",
            "end_datetime",
            "academic_year",
            "school",
            "course",
            "semester",
            "year_level",
            "student_type",
            "created_at",
            "updated_at",
        )
        extra_kwargs = {
            "status": {
                "help_text": choices_help_text(models.EnrollmentSchedule.Statuses)
            }
        }
