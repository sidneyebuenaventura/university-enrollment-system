from django.contrib import admin

from . import models


@admin.register(models.ModuleConfiguration)
class ModuleConfigurationAdmin(admin.ModelAdmin):
    list_display = ["module", "is_active"]


class EnrollmentScheduleEventInline(admin.TabularInline):
    model = models.EnrollmentScheduleEvent
    extra = 0


@admin.register(models.EnrollmentSchedule)
class EnrollmentScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "config",
        "_school",
        "_course",
        "school_year",
        "semester",
        "start_datetime",
        "end_datetime",
    )
    list_filter = ("config", "school", "semester")
    raw_id_fields = ("course",)
    inlines = (EnrollmentScheduleEventInline,)

    def _school(self, obj):
        if obj.school:
            return obj.school.code
        return "All"

    def _course(self, obj):
        if obj.course:
            return obj.course.sub_code
        return "All"
