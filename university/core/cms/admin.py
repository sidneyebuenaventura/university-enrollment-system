from django.contrib import admin
from nested_inline import admin as nested_admin

from . import models


@admin.register(models.Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")


@admin.register(models.Classification)
class ClassificationAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")


@admin.register(models.Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = (
        "school",
        "classification",
        "building",
        "number",
        "floor_no",
        "wing",
        "is_active",
        "is_lecture_room",
    )
    list_filter = (
        "is_active",
        "is_lecture_room",
    )
    raw_id_fields = (
        "school",
        "classification",
        "building",
    )


@admin.register(models.Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "sub_code", "name", "category", "is_active")
    raw_id_fields = ("school",)
    search_fields = [
        "code",
        "sub_code",
        "name",
    ]
    list_filter = (
        "is_active",
        "school",
        "level",
        "category",
    )


@admin.register(models.SubjectGrouping)
class SubjectGroupingAdmin(admin.ModelAdmin):
    list_display = ("name", "ref_id", "is_gen_ed")
    raw_id_fields = ("department",)


@admin.register(models.Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = (
        "ref_id",
        "course_code",
        "course_number",
        "descriptive_code",
        "descriptive_title",
    )
    raw_id_fields = ("school", "grouping")
    search_fields = [
        "ref_id",
        "course_code",
        "course_number",
        "descriptive_code",
        "charge_code",
    ]
    list_filter = (
        "school",
        "charge_code",
    )


class CurriculumSubjectNestedInline(nested_admin.NestedTabularInline):
    model = models.CurriculumSubject
    extra = 0
    raw_id_fields = ("subject",)


class CurriculumPeriodNestedInline(nested_admin.NestedTabularInline):
    model = models.CurriculumPeriod
    # extra = 0
    inlines = (CurriculumSubjectNestedInline,)


class CurriculumPeriodInline(admin.TabularInline):
    model = models.CurriculumPeriod
    ordering = (
        "year_level",
        "order",
    )


@admin.register(models.Curriculum)
class CurriculumAdmin(nested_admin.NestedModelAdmin):
    list_display = (
        "ref_id",
        "effective_start_year",
        "effective_end_year",
        "effective_semester",
        "is_current",
    )
    list_filter = (
        "is_current",
        "effective_semester",
    )
    raw_id_fields = ("course",)
    search_fields = ["ref_id", "effective_start_year"]
    inlines = (CurriculumPeriodInline,)


class CurriculumSubjectInline(admin.TabularInline):
    model = models.CurriculumSubject
    raw_id_fields = ("curriculum_period", "subject")


@admin.register(models.CurriculumPeriod)
class CurriculumPeriodAdmin(admin.ModelAdmin):
    list_display = (
        "curriculum",
        "semester",
        "year_level",
    )
    list_filter = (
        "semester",
        "year_level",
    )
    raw_id_fields = ("curriculum",)
    inlines = (CurriculumSubjectInline,)


class ClassScheduleInline(admin.TabularInline):
    model = models.ClassSchedule
    raw_id_fields = ("room",)


@admin.register(models.CurriculumSubject)
class CurriculumSubjectAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "curriculum_period")
    list_filter = ("subject_class", "category_rate")
    raw_id_fields = ("subject", "curriculum_period")


@admin.register(models.Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = (
        "class_code",
        "semester",
        "subject",
        "year_level",
        "course",
        "instructor",
        "is_dissolved",
    )
    list_filter = (
        "is_dissolved",
        "is_crash_course",
        "is_intercollegiate",
        "is_external_class",
        "semester",
    )
    raw_id_fields = ("subject", "instructor", "course", "tuition_fee_rate")
    inlines = (ClassScheduleInline,)
    search_fields = ["class_code"]
    ordering = ("-semester",)


@admin.register(models.Fee)
class FeeAdmin(admin.ModelAdmin):
    list_display = (
        "academic_year",
        "code",
        "name",
        "description",
        "amount",
        "is_active",
        "type",
    )
    list_filter = ("is_active", "academic_year")
    raw_id_fields = ("academic_year",)
    search_fields = ["code"]


@admin.register(models.MiscellaneousFeeSpecification)
class MiscellaneousFeeSpecificationAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "academic_year",
        "code",
        "semester_from",
        "semester_to",
    )
    search_fields = ["code"]
    raw_id_fields = ("school", "subject", "academic_year")
    list_filter = ("academic_year",)


@admin.register(models.OtherFeeSpecification)
class OtherFeeSpecificationSpecificationAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "academic_year",
        "code",
        "semester_from",
        "semester_to",
    )
    search_fields = ["code"]
    raw_id_fields = ("school", "subject", "academic_year")
    list_filter = ("academic_year",)


class TuitionFeeRateInline(admin.TabularInline):
    model = models.TuitionFeeRate
    ordering = ("-academic_year__year_start",)


@admin.register(models.TuitionFeeCategory)
class TuitionFeeCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "ref_id",
        "category",
        "year_level",
    )
    list_filter = ("year_level",)
    inlines = (TuitionFeeRateInline,)
    search_fields = ["ref_id", "category"]


@admin.register(models.Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "type",
        "percentage",
        "apply_to",
        "is_confirmed",
    )
    list_filter = ("type", "is_confirmed")
    search_fields = ["type", "name", "ref_id"]
    raw_id_fields = ("department",)


@admin.register(models.LaboratoryFee)
class LaboratoryFeeAdmin(admin.ModelAdmin):
    list_display = ("subject", "academic_year", "rate")
    list_filter = ("academic_year",)
    search_fields = ["subject__course_code"]
    ordering = ("academic_year",)
    raw_id_fields = ("academic_year", "subject")


@admin.register(models.RemarkCode)
class RemarkCodeAdmin(admin.ModelAdmin):
    list_display = ("ref_id", "description", "department")
    list_filter = ("department",)
    search_fields = [
        "description",
    ]
    ordering = ("ref_id",)
    raw_id_fields = ("department",)


@admin.register(models.ClassGradeState)
class ClassGradeStateAdmin(admin.ModelAdmin):
    list_display = (
        "klass",
        "prelim_grade_state",
        "midterm_grade_state",
        "tentative_final_grade_state",
        "final_grade_state",
    )
    raw_id_fields = ("klass",)
    search_fields = ["klass__class_code"]


@admin.register(models.TuitionFeeRate)
class TuitionFeeRateAdmin(admin.ModelAdmin):
    list_display = ("tuition_fee_category", "academic_year", "rate")
    raw_id_fields = ("tuition_fee_category",)


@admin.register(models.Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "is_active")
