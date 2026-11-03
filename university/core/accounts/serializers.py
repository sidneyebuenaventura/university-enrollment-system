from dj_rest_auth.models import TokenModel
from dj_rest_auth.serializers import LoginSerializer as DefaultLoginSerializer
from dj_rest_auth.serializers import (
    PasswordChangeSerializer as DefaultPasswordChangeSerializer,
)
from dj_rest_auth.serializers import TokenSerializer as DefaultTokenSerializer
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db.models import Q
from rest_framework import exceptions, serializers
from rest_framework.validators import UniqueValidator

from university.framework.serializers import (
    DryRunModelSerializer,
    inline_serializer_class,
)

from . import models, selectors, services

User = get_user_model()


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ("id", "codename", "name")


class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Module
        fields = ("id", "name", "description", "codename", "sub_name", "category")


class RoleModuleSerializer(serializers.ModelSerializer):
    module = ModuleSerializer()

    class Meta:
        model = models.RoleModule
        fields = (
            "module",
            "has_view_perm",
            "has_add_perm",
            "has_change_perm",
            "has_delete_perm",
        )


class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()
    modules = serializers.SerializerMethodField()
    role_modules = serializers.SerializerMethodField()

    class Meta:
        model = models.Role
        fields = ("id", "name", "permissions", "modules", "role_modules")

    def get_permissions(self, obj):
        permissions = []
        for perm in obj.permissions.all():
            permissions.append(f"{perm.content_type.app_label}.{perm.codename}")
        return permissions

    def get_modules(self, obj):
        modules = obj.modules.filter(
            Q(rolemodule__has_view_perm=True) | Q(rolemodule__has_change_perm=True)
        )
        return ModuleSerializer(modules, many=True).data

    def get_role_modules(self, obj):
        role_modules = obj.rolemodule_set.filter(
            Q(has_view_perm=True) | Q(has_change_perm=True)
        )
        return RoleModuleSerializer(role_modules, many=True).data


class StaffSchoolGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.UserSchoolGroup
        fields = (
            "school",
            "roles",
        )


class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ("id", "name", "is_active")
        model = models.School


class StaffSchoolGroupRetrieveSerializer(serializers.ModelSerializer):
    roles = RoleSerializer(many=True)
    school = SchoolSerializer()

    class Meta:
        model = models.UserSchoolGroup
        fields = (
            "school",
            "roles",
        )


class StaffCreateSerializer(DryRunModelSerializer):
    email = serializers.CharField(
        required=True,
        validators=[
            UniqueValidator(
                queryset=models.User.objects.all(), message="Email already registered."
            )
        ],
    )
    password1 = serializers.CharField(required=True, write_only=True)
    password2 = serializers.CharField(required=True, write_only=True)
    departments = serializers.ListField(
        child=serializers.IntegerField(), write_only=True
    )
    school_groups = StaffSchoolGroupSerializer(many=True)

    class Meta:
        model = models.User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "password1",
            "password2",
            "status",
            "departments",
            "school_groups",
            "modules",
        )

    def validate(self, data):
        if data["password1"] != data["password2"]:
            raise serializers.ValidationError("The two password fields didn't match.")
        return data


class StaffUpdateSerializer(DryRunModelSerializer):
    email = serializers.CharField(
        required=True,
        validators=[
            UniqueValidator(
                queryset=models.User.objects.all(), message="Email already registered."
            )
        ],
    )
    departments = serializers.ListField(
        child=serializers.IntegerField(), write_only=True
    )
    school_groups = StaffSchoolGroupSerializer(many=True)

    class Meta:
        model = models.User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "status",
            "departments",
            "school_groups",
            "modules",
        )


class UserDetailsBaseSerializer(serializers.ModelSerializer):
    email = serializers.CharField(
        required=True,
        validators=[
            UniqueValidator(
                queryset=models.User.objects.all(), message="Email already registered."
            )
        ],
    )
    modules = serializers.SerializerMethodField()

    def get_modules(self, obj) -> ModuleSerializer(many=True):
        modules = selectors.user_modules_get(user=obj)
        return ModuleSerializer(modules, many=True).data


class UserDetailsSerializer(UserDetailsBaseSerializer):
    class RoleModuleObjectSerializer(serializers.Serializer):
        name = serializers.CharField()
        description = serializers.CharField()
        codename = serializers.CharField()
        has_view_perm = serializers.BooleanField()
        has_add_perm = serializers.BooleanField()
        has_change_perm = serializers.BooleanField()
        has_delete_perm = serializers.BooleanField()

    ModuleSerializer = inline_serializer_class(
        model=models.Module,
        fields=("name", "sub_name", "description", "codename", "category"),
    )
    SchoolSerializer = inline_serializer_class(
        model=models.School, fields=("id", "name")
    )
    SchoolGroupSerializer = inline_serializer_class(
        model=models.UserSchoolGroup,
        fields=("school", "modules"),
        declared_fields={
            "school": SchoolSerializer(),
            "modules": RoleModuleObjectSerializer(source="get_role_modules", many=True),
        },
    )

    schools = serializers.SerializerMethodField()
    school_groups = serializers.SerializerMethodField()
    groups = RoleSerializer(many=True)
    modules = serializers.SerializerMethodField()
    password_rem_days = serializers.SerializerMethodField()

    class Meta:
        model = models.User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "status",
            "is_first_login",
            "password_rem_days",
            "schools",
            "school_groups",
            "groups",
            "modules",
        )

    def get_schools(self, obj) -> SchoolSerializer(many=True):
        schools = selectors.user_schools_get(user=obj)
        return self.SchoolSerializer(schools, many=True).data

    def get_school_groups(self, obj) -> SchoolGroupSerializer(many=True):
        school_groups = obj.school_groups.all()
        return self.SchoolGroupSerializer(school_groups, many=True).data

    def get_modules(self, obj) -> RoleModuleObjectSerializer(many=True):
        role_modules = selectors.user_role_modules_data_get(user=obj)
        joint_modules = selectors.user_modules_join(user=obj, role_modules=role_modules)

        return self.RoleModuleObjectSerializer(joint_modules, many=True).data

    def get_password_rem_days(self, obj) -> int:
        return obj.get_password_rem_days()


class StudentUserDetailsSerializer(UserDetailsBaseSerializer):
    student = serializers.SerializerMethodField()
    modules = serializers.SerializerMethodField()
    password_rem_days = serializers.SerializerMethodField()

    class Meta:
        model = models.User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_first_login",
            "password_rem_days",
            "student",
            "modules",
        )

    def get_student(self, obj):
        from university.core.students.serializers import StudentRetrieveSerializer

        return StudentRetrieveSerializer(obj.student).data

    def get_password_rem_days(self, obj) -> int:
        return obj.get_password_rem_days()


class WebLoginSerializer(DefaultLoginSerializer):
    email = None
    username = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(style={"input_type": "password"})

    @staticmethod
    def validate_auth_user_status(user):
        DefaultLoginSerializer.validate_auth_user_status(user)

        if not user.is_superuser and user.type != models.User.Types.ADMIN:
            raise exceptions.ValidationError("Unauthorized login")


class MobileLoginSerializer(DefaultLoginSerializer):
    email = None
    username = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(style={"input_type": "password"})

    @staticmethod
    def validate_auth_user_status(user):
        DefaultLoginSerializer.validate_auth_user_status(user)

        if user.type != models.User.Types.STUDENT:
            raise exceptions.ValidationError("Unauthorized login")


class TokenSerializer(DefaultTokenSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = TokenModel
        fields = (
            "key",
            "user",
        )

    def get_user(self, obj):
        if obj.user.is_superuser or obj.user.type == models.User.Types.ADMIN:
            return UserDetailsSerializer(obj.user).data
        elif obj.user.type == models.User.Types.STUDENT:
            return StudentUserDetailsSerializer(obj.user).data


class PasswordChangeSerializer(DefaultPasswordChangeSerializer):
    def custom_validation(self, attrs):
        new_password = attrs.get("new_password2")
        password_history = selectors.user_password_history_get(
            user=self.user, password=new_password
        )

        if password_history:
            error_msg = "Using your last 2 passwords is not allowed."
            raise serializers.ValidationError(error_msg)

        if self.user.type == User.Types.STUDENT:
            student = self.user.student

            if student.first_name.lower() in new_password.lower():
                error_msg = "The password is too similar to the first name."
                raise serializers.ValidationError(error_msg)

            if student.last_name.lower() in new_password.lower():
                error_msg = "The password is too similar to the last name."
                raise serializers.ValidationError(error_msg)

            if student.email:
                email_name = student.email.split("@")[0]

                if email_name.lower() in new_password.lower():
                    error_msg = "The password is too similar to the email."
                    raise serializers.ValidationError(error_msg)

    def save(self):
        super().save()
        services.user_password_history_create(
            user=self.user, hashed_password=self.user.password
        )


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ("id", "name")
        model = models.Department


class StaffListRetrieveSerializer(serializers.ModelSerializer):
    departments = DepartmentSerializer(many=True)
    groups = RoleSerializer(many=True)
    school_groups = StaffSchoolGroupRetrieveSerializer(many=True)
    modules = ModuleSerializer(many=True)
    permissions = serializers.ReadOnlyField()

    class Meta:
        model = models.User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "status",
            "created_at",
            "departments",
            "groups",
            "permissions",
            "school_groups",
            "modules",
        )


class RoleModuleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.RoleModule
        fields = (
            "module",
            "has_view_perm",
            "has_add_perm",
            "has_change_perm",
            "has_delete_perm",
        )


class RoleCreateUpdateSerializer(serializers.ModelSerializer):
    role_modules = RoleModuleCreateSerializer(many=True, write_only=True)

    class Meta:
        model = models.Role
        fields = ("id", "name", "role_modules")


class UserDetailBaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "status",
            "departments",
            "last_login",
        )


class FacultyBaseSerializer(serializers.ModelSerializer):
    user = UserDetailBaseSerializer()

    class Meta:
        model = models.Personnel
        fields = ("id", "user", "emp_id", "category")


class FacultyDetailSerializer(serializers.ModelSerializer):
    user = UserDetailBaseSerializer()
    subject_classes = serializers.SerializerMethodField()

    class Meta:
        model = models.Personnel
        fields = "__all__"

    def get_subject_classes(self, obj):
        from university.core.cms.serializers import ClassSerializer

        return ClassSerializer(
            selectors.faculty_current_schedule_list_get(obj), many=True
        ).data


class SemesterSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Semester
        fields = ("id", "term", "date_start", "date_end", "order")


class AcademicYearBaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.AcademicYear
        fields = ("id", "year_start", "year_end", "date_start", "date_end")


class AcademicYearSerializer(serializers.ModelSerializer):
    semesters = SemesterSerializer(many=True)

    class Meta:
        model = models.AcademicYear
        fields = ("id", "year_start", "year_end", "date_start", "date_end", "semesters")


class AcademicYearCurrentRetrieveSerializer(serializers.ModelSerializer):
    current_semester = serializers.SerializerMethodField()

    class Meta:
        model = models.AcademicYear
        fields = (
            "year_start",
            "year_end",
            "date_start",
            "date_end",
            "current_semester",
        )

    def get_current_semester(self, obj) -> SemesterSerializer:
        return SemesterSerializer(selectors.current_semester_get()).data


class SemesterUpcomingRetrieveSerializer(serializers.ModelSerializer):
    AcademicYearSerializer = inline_serializer_class(
        model=models.AcademicYear,
        fields=("id", "year_start", "year_end", "date_start", "date_end"),
    )

    academic_year = AcademicYearSerializer()

    class Meta:
        model = models.Semester
        fields = ("academic_year", "term", "date_start", "date_end", "order")


class PersonnelProfileRetrieveSerializer(serializers.ModelSerializer):
    RoleSerializer = inline_serializer_class(
        model=models.Role,
        fields=("name",),
    )

    PersonnelSerializer = inline_serializer_class(
        model=models.Personnel,
        fields=("__all__"),
    )

    fullname = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    personnel = serializers.SerializerMethodField()

    class Meta:
        model = models.User
        fields = ("username", "email", "fullname", "roles", "personnel")

    def get_roles(self, obj) -> list[RoleSerializer]:
        return self.RoleSerializer(obj.groups.all(), many=True).data

    def get_fullname(self, obj) -> str:
        if hasattr(obj, "personnel"):
            return obj.personnel.fullname
        return None

    def get_personnel(self, obj) -> PersonnelSerializer:
        if hasattr(obj, "personnel"):
            return self.PersonnelSerializer(obj.personnel).data
        return None


class SemesterPreviousRetrieveSerializer(serializers.ModelSerializer):
    AcademicYearSerializer = inline_serializer_class(
        model=models.AcademicYear,
        fields=("id", "year_start", "year_end", "date_start", "date_end"),
    )

    academic_year = AcademicYearSerializer()

    class Meta:
        model = models.Semester
        fields = ("id", "academic_year", "term", "date_start", "date_end", "order")
