from django.contrib import admin, messages
from django_object_actions import DjangoObjectActions
from nested_inline import admin as nested_admin

from university.framework.exceptions import ServiceException

from . import models
from .services import student_password_generate, test_student_create


@admin.register(models.Student)
class StudentAdmin(DjangoObjectActions, admin.ModelAdmin):
    list_display = (
        "id_number",
        "applicant_number",
        "last_name",
        "first_name",
        "type",
        "course",
    )
    fieldsets = (
        (
            "ID References",
            {
                "fields": (
                    "id_number",
                    "applicant_number",
                    "is_previous_number",
                )
            },
        ),
        (
            "Academic Information",
            {
                "fields": (
                    "course",
                    "curriculum",
                    "semester",
                    "year_level",
                )
            },
        ),
        (
            "Personal info",
            {
                "fields": (
                    "user",
                    "first_name",
                    "middle_name",
                    "last_name",
                    "birth_date",
                    "birth_place",
                    "gender",
                    "civil_status",
                    "citizenship",
                    "nationality",
                    "religion",
                    "senior_high_strand",
                )
            },
        ),
        (
            "Contact Information",
            {
                "fields": (
                    "street",
                    "barangay",
                    "city",
                    "zip_code",
                    "phone_no",
                    "home_phone_no",
                    "local_address",
                    "local_phone_no",
                    "guardian_name",
                    "guardian_address",
                )
            },
        ),
        (
            "Family Background",
            {
                "fields": (
                    "father_name",
                    "father_occupation",
                    "mother_name",
                    "mother_occupation",
                    "spouse_name",
                    "spouse_address",
                    "spouse_phone_no",
                )
            },
        ),
        (
            "Important dates",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "deleted_at",
                    "date_created",
                )
            },
        ),
    )

    raw_id_fields = (
        "user",
        "course",
        "curriculum",
    )
    readonly_fields = (
        "id_number",
        "applicant_number",
        "created_at",
        "updated_at",
        "deleted_at",
    )
    list_filter = (
        "gender",
        "civil_status",
        "citizenship",
        "nationality",
        "type",
        "course",
    )
    search_fields = [
        "first_name",
        "last_name",
        "id_number",
        "applicant_number",
        "user__username",
    ]
    change_actions = ("generate_test_data", "generate_password")

    def generate_test_data(self, request, obj):
        try:
            test_student_create(
                username=obj.user.username,
                email=obj.user.email,
                first_name=obj.first_name,
                last_name=obj.last_name,
                student_number=obj.id_number,
            )
        except ServiceException as e:
            messages.error(str(e))
        else:
            messages.success(
                request, f"{obj.id_number} test data generation succcessful."
            )

    generate_test_data.label = "Generate Test Data"
    generate_test_data.short_description = "Generates student test data"

    def generate_password(self, request, obj):
        student_password_generate(student=obj, override=True)
        messages.success(
            request,
            f"{obj.id_number} password generation succcessful. Instructions has been sent to {obj.email}",
        )

    generate_password.label = "Generate Password"
    generate_password.short_description = (
        "Generates student password and sends an email instruction"
    )


class EnrolledClassInline(admin.TabularInline):
    model = models.EnrolledClass
    raw_id_fields = ("klass",)
    extra = 0


class ClassGradeNestedInline(nested_admin.NestedStackedInline):
    model = models.EnrolledClassGrade
    extra = 0
    raw_id_fields = ("subject",)


class EnrolledClassNestedInline(nested_admin.NestedTabularInline):
    model = models.EnrolledClass
    extra = 0
    raw_id_fields = ("klass", "curriculum_subject", "equivalent_subject")
    exclude = ("student",)
    inlines = (ClassGradeNestedInline,)


@admin.register(models.Enrollment)
class EnrollmentAdmin(nested_admin.NestedModelAdmin):
    list_display = (
        "student",
        "semester",
        "year_level",
        "step",
        "status",
    )
    raw_id_fields = (
        "student",
        "academic_year",
        "semester",
        "miscellaneous_fee_specification",
        "other_fee_specification",
    )
    search_fields = [
        "student__first_name",
        "student__last_name",
        "student__id_number",
    ]
    list_filter = ("academic_year", "semester", "status", "step")
    inlines = (EnrolledClassNestedInline,)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "student",
                    "academic_year",
                    "semester",
                    "year_level",
                    "status",
                    "step",
                ),
            },
        ),
        (
            "Information",
            {
                "fields": (
                    "current_address",
                    "contact_number",
                    "personal_email",
                    "institutional_email",
                    "father_name",
                    "father_phone_no",
                    "father_email",
                    "mother_name",
                    "mother_phone_no",
                    "mother_email",
                    "is_living_with_parents",
                    "emergency_contact_name",
                    "emergency_contact_address",
                    "emergency_contact_phone_no",
                    "emergency_contact_email",
                )
            },
        ),
        (
            "Fee",
            {
                "fields": (
                    "miscellaneous_fee_specification",
                    "other_fee_specification",
                )
            },
        ),
    )


@admin.register(models.EnrollmentDiscount)
class EnrollmentDiscountClassAdmin(admin.ModelAdmin):
    raw_id_fields = (
        "enrollment",
        "personnel",
        "dependent_personnel",
        "siblings",
        "validated_discount",
    )
    search_fields = ["enrollment"]
    ordering = ("-created_at",)
    list_display = ("enrollment",)


@admin.register(models.EnrollmentStatus)
class EnrollmentStatusAdmin(admin.ModelAdmin):
    list_display = ("enrollment", "block_status", "is_for_manual_tagging")
    list_filter = ("is_for_manual_tagging", "block_status")
    search_fields = ["enrollment"]
    ordering = ("-created_at",)
    raw_id_fields = ("enrollment",)


@admin.register(models.EnrolledClass)
class EnrolledClassAdmin(admin.ModelAdmin):
    raw_id_fields = (
        "student",
        "enrollment",
        "klass",
        "curriculum_subject",
        "equivalent_subject",
    )


@admin.register(models.EnrolledClassGrade)
class EnrolledClassGradeAdmin(admin.ModelAdmin):
    pass


class GradeSheetRowInline(admin.TabularInline):
    model = models.GradeSheetRow
    extra = 0


@admin.register(models.GradeSheet)
class GradeSheetAdmin(admin.ModelAdmin):
    raw_id_fields = ("klass",)
    inlines = (GradeSheetRowInline,)


@admin.register(models.EnrollmentGrade)
class EnrollmentGradeAdmin(admin.ModelAdmin):
    list_display = ("enrollment", "general_weighted_average", "grading_status")
    list_filter = ("enrollment__semester", "grading_status")
    search_fields = ["enrollment__student__id_number"]
    ordering = ("-created_at",)
    raw_id_fields = ("enrollment",)


@admin.register(models.GeneralWeightedAverageSheet)
class GeneralWeightedAverageSheetAdmin(admin.ModelAdmin):
    list_display = ("file_id", "file", "status", "created_at")


@admin.register(models.ChangeScheduleRequest)
class ChangeScheduleRequestAdmin(admin.ModelAdmin):
    list_display = ("request_no", "status", "created_at")
    raw_id_fields = ("student",)


@admin.register(models.AddSubjectRequest)
class AddSubjectRequestRequestAdmin(admin.ModelAdmin):
    list_display = ("request_no", "status", "created_at")
    raw_id_fields = ("student",)


@admin.register(models.OpenClassRequest)
class OpenClassRequestAdmin(admin.ModelAdmin):
    list_display = ("request_no", "status", "created_at")
    raw_id_fields = ("student",)


@admin.register(models.WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ("request_no", "category", "type", "status", "created_at")
    raw_id_fields = ("student",)


@admin.register(models.StudentRequestReviewHistory)
class StudentRequestReviewHistoryAdmin(admin.ModelAdmin):
    list_display = ("request", "status", "remarks")
