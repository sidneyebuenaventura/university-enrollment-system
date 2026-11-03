from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from . import models


@admin.register(models.Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "sub_name",
        "category",
        "codename",
        "description",
        "user_count",
    )
    list_filter = ("platform", "category")
    exclude = ("users",)

    def user_count(self, obj):
        return obj.users.count()


@admin.register(models.RoleModule)
class RoleModuleAdmin(admin.ModelAdmin):
    list_display = ("role", "module", "has_view_perm", "has_change_perm")
    list_filter = ["role", "module"]


@admin.register(models.PasswordHistory)
class PasswordHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "type", "created_at")
    raw_id_fields = ("user",)
    list_filter = ("type",)
    search_fields = ["user__username"]
    exclude = ("value",)


@admin.register(models.User)
class UserAdmin(BaseUserAdmin):
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "deleted_at",
                    "created_at",
                    "updated_at",
                    "status",
                )
            },
        ),
    )
    fieldsets = (
        (None, {"fields": ("username", "password", "status", "is_first_login")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                ),
            },
        ),
        (
            "Important dates",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "deleted_at",
                    "last_login",
                    "date_joined",
                )
            },
        ),
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(models.School)
class SchooolAdmin(admin.ModelAdmin):
    list_display = ("name", "ref_id", "is_active")
    list_filter = ["is_active"]
    raw_id_fields = ("dean",)


@admin.register(models.UserSchoolGroup)
class UserSchoolGroupAdmin(admin.ModelAdmin):
    list_display = ("school", "user")
    raw_id_fields = ("user",)


@admin.register(models.Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "ref_id", "code")
    raw_id_fields = ["main_department", "department_head", "school", "users"]
    search_fields = ["ref_id", "code"]


@admin.register(models.Personnel)
class PersonnelAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "ref_id",
        "emp_id",
        "category",
        "last_name",
        "first_name",
    )
    fieldsets = (
        (
            "ID References",
            {
                "fields": (
                    "ref_id",
                    "emp_id",
                    "old_id",
                    "sss_no",
                    "tin",
                    "license_no",
                    "pagibig_no",
                    "philhealth_no",
                    "rank",
                    "category",
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
                    "maiden_name",
                    "birth_date",
                    "birth_place",
                    "gender",
                    "civil_status",
                    "nationality",
                    "union_affiliation",
                    "religion",
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
                    "relative_name",
                    "relative_relationship",
                    "relative_address",
                    "relative_phone_no",
                )
            },
        ),
        (
            "Family Background",
            {
                "fields": (
                    "father_name",
                    "mother_name",
                    "spouse_name",
                    "spouse_occupation",
                    "no_of_child",
                    "marriage_date",
                    "separation_date",
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
                    "employment_date",
                )
            },
        ),
    )

    raw_id_fields = ("user",)
    readonly_fields = (
        "ref_id",
        "emp_id",
        "old_id",
        "created_at",
        "updated_at",
        "deleted_at",
        "employment_date",
    )
    list_filter = ("category", "gender", "civil_status", "nationality", "rank")
    search_fields = ["first_name", "last_name", "ref_id"]


@admin.register(models.Semester)
class SemesterAdmin(admin.ModelAdmin):
    pass


class SemesterInline(admin.TabularInline):
    model = models.Semester
    ordering = ("order",)


@admin.register(models.AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = (
        "year_start",
        "year_end",
        "date_start",
        "date_end",
    )
    inlines = (SemesterInline,)
    search_fields = ["year_start", "category"]
    ordering = ("-year_start",)
