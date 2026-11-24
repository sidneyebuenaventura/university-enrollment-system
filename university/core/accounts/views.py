from dj_rest_auth.views import LoginView
from dj_rest_auth.views import LogoutView as RestAuthLogoutView
from dj_rest_auth.views import PasswordChangeView as RestPasswordChangeView
from dj_rest_auth.views import UserDetailsView as RestUserDetailsView
from django.contrib.auth.models import Permission
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import serializers as rest_serializers
from rest_framework import status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import GenericAPIView, ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import Serializer as EmptySerializer
from rest_framework.viewsets import ModelViewSet

from config.settings.openapi import Tags
from university.framework.events import EventObject, event_publisher
from university.framework.pagination import PageNumberPagination
from university.framework.permissions import (
    IsAdminUser,
    IsAdminUserNPC,
    IsNewAdminUser,
    IsNewStudentUser,
    IsStudentUserNPC,
    IsSuperUserNPC,
)
from university.framework.views import (
    DryRunModelViewSet,
    ListRetrieveViewSet,
    PermissionRequiredMixin,
    ViewSetSerializerClassMixin,
)

from .. import events
from . import models, selectors, serializers, services


class WebLoginView(LoginView):
    """Web Login

    Authentication endpoint for Admin Portal built with ReactJS.
    """

    serializer_class = serializers.WebLoginSerializer


class MobileLoginView(LoginView):
    """Mobile Login

    Authentication endpoint for Student Portal built with Flutter.
    """

    serializer_class = serializers.MobileLoginSerializer


class LogoutView(RestAuthLogoutView):
    """Logout"""


class PasswordSetView(GenericAPIView):
    """Password Set"""

    class InputSerializer(rest_serializers.Serializer):
        password1 = rest_serializers.CharField()
        password2 = rest_serializers.CharField()

        def validate(self, attrs):
            if attrs.get("password1") != attrs.get("password2"):
                raise rest_serializers.ValidationError("Passwords does not match.")

            return attrs

    serializer_class = InputSerializer
    permission_classes = [IsAuthenticated, IsNewAdminUser | IsNewStudentUser]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        services.user_password_set(
            user=request.user,
            password=data.get("password1"),
        )

        return Response(
            {"detail": "New password has been set."}, status=status.HTTP_200_OK
        )


class PasswordChangeWaiveView(GenericAPIView):
    """Password Change Waive"""

    serializer_class = EmptySerializer
    permission_classes = [
        IsAuthenticated,
        IsSuperUserNPC | IsAdminUserNPC | IsStudentUserNPC,
    ]

    def post(self, request):
        services.user_password_history_create(
            user=request.user,
            type=models.PasswordHistory.Types.WAIVED,
        )

        return Response(
            {"detail": "Change Password has been waived."}, status=status.HTTP_200_OK
        )


class PasswordChangeView(RestPasswordChangeView):
    """Password Change"""

    permission_classes = [IsAuthenticated, IsAdminUserNPC | IsStudentUserNPC]


class PasswordResetView(GenericAPIView):
    """Password Reset"""

    class InputSerializer(rest_serializers.Serializer):
        id_number = rest_serializers.CharField()
        birth_date = rest_serializers.DateField()

    serializer_class = InputSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        services.user_password_reset(
            id_number=data.get("id_number"),
            birth_date=data.get("birth_date"),
            raise_exception=True,
        )

        return Response(
            {"detail": "Password reset e-mail has been sent."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(GenericAPIView):
    """Password Reset Confirm"""

    class InputSerializer(rest_serializers.Serializer):
        uid = rest_serializers.CharField()
        token = rest_serializers.CharField()
        new_password1 = rest_serializers.CharField()
        new_password2 = rest_serializers.CharField()

        def validate(self, attrs):
            if attrs.get("new_password1") != attrs.get("new_password2"):
                raise rest_serializers.ValidationError("Passwords does not match.")

            return attrs

    serializer_class = InputSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        services.user_password_reset_confirm(
            uid=data.get("uid"),
            token=data.get("token"),
            password=data.get("new_password1"),
        )

        return Response(
            {"detail": "Password has been reset with the new password."},
            status=status.HTTP_200_OK,
        )


class UserDetailsView(RestUserDetailsView):
    serializer_class = serializers.UserDetailsSerializer

    serializer_classes_by_type = {
        models.User.Types.ADMIN.value: serializers.UserDetailsSerializer,
        models.User.Types.STUDENT.value: serializers.StudentUserDetailsSerializer,
    }

    def get_serializer_class(self):
        obj = self.get_object()
        return (
            self.serializer_classes_by_type.get(obj.type.value) or self.serializer_class
        )


class StaffViewSet(
    ViewSetSerializerClassMixin, PermissionRequiredMixin, DryRunModelViewSet
):
    queryset = models.User.active_objects.filter(is_staff=True)
    pagination_class = PageNumberPagination

    serializer_class = serializers.StaffUpdateSerializer
    serializer_classes = {
        "create": serializers.StaffCreateSerializer,
        "list": serializers.StaffListRetrieveSerializer,
        "retrieve": serializers.StaffListRetrieveSerializer,
        "update": serializers.StaffUpdateSerializer,
        "partial_update": serializers.StaffUpdateSerializer,
        "destroy": EmptySerializer,
    }

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = [
        "is_active",
    ]
    search_fields = ["username", "first_name", "last_name"]
    ordering_fields = ["username", "first_name", "last_name", "status"]
    ordering = ["first_name", "last_name"]

    permission_classes = [IsAuthenticated, IsAdminUser]
    permission = ["core_accounts.view_user"]
    permissions = {
        "create": ["core_accounts.add_user"],
        "list": ["core_accounts.view_user"],
        "retrieve": ["core_accounts.view_user"],
        "update": ["core_accounts.change_user"],
        "partial_update": ["core_accounts.change_user"],
        "destroy": ["core_accounts.delete_user"],
    }

    def perform_create(self, serializer):
        user = services.staff_create(serializer.validated_data)
        serializer.instance = user
        # TODO: Fix object serialization for event publishing
        # event = ModelEvent(events.STAFF_CREATED, actor=self.request.user, target=user)
        # event.publish()

    def perform_update(self, serializer):
        user = self.get_object()
        # data_before_update = user.to_dict()

        user = services.staff_update(user=user, data=serializer.validated_data)
        serializer.instance = user

        # TODO: Fix object serialization for event publishing
        # event = ModelEvent(
        #     events.STAFF_UPDATED,
        #     actor=self.request.user,
        #     target=user,
        #     old_target=data_before_update,
        # )
        # event.publish()

    def perform_destroy(self, instance):
        services.staff_delete(user=instance)


class ModuleListAPIView(ListAPIView):
    queryset = models.Module.objects.filter(
        platform=models.Module.Platforms.WEB
    ).order_by("order")
    serializer_class = serializers.ModuleSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = {"category": ["in"]}
    search_fields = ["name", "codename", "sub_name"]


class PermissionListAPIView(ListAPIView):
    queryset = Permission.objects.all()
    serializer_class = serializers.PermissionSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]


class RoleViewSet(ViewSetSerializerClassMixin, PermissionRequiredMixin, ModelViewSet):
    queryset = models.Role.admin_objects.all()
    pagination_class = PageNumberPagination

    serializer_class = serializers.RoleCreateUpdateSerializer
    serializer_classes = {
        "create": serializers.RoleCreateUpdateSerializer,
        "list": serializers.RoleSerializer,
        "retrieve": serializers.RoleSerializer,
        "update": serializers.RoleCreateUpdateSerializer,
        "partial_update": serializers.RoleCreateUpdateSerializer,
        "destroy": EmptySerializer,
    }

    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name"]
    ordering = ["name"]

    permission_classes = [IsAuthenticated, IsAdminUser]
    permission = ["auth.view_group"]
    permissions = {
        "create": ["auth.add_group"],
        "list": ["auth.view_group"],
        "retrieve": ["auth.view_group"],
        "update": ["auth.change_group"],
        "partial_update": ["auth.change_group"],
        "destroy": ["auth.delete_group"],
    }

    def perform_create(self, serializer):
        role = services.role_create(data=serializer.validated_data)
        serializer.instance = role
        event_publisher.create(
            name=events.ROLE_CREATED, actor=self.request.user, target=role
        )

    def perform_update(self, serializer):
        role = self.get_object()
        role_before = EventObject(role)

        role = services.role_update(role=role, data=serializer.validated_data)
        serializer.instance = role

        role_after = EventObject(role)
        event_publisher.update(
            name=events.ROLE_UPDATED,
            actor=self.request.user,
            old_target=role_before,
            new_target=role_after,
        )

    def perform_destroy(self, serializer):
        role = self.get_object()
        target = EventObject(role)
        services.role_destroy(role=role)
        serializer.instance = role
        event_publisher.delete(
            name=events.ROLE_DELETED, actor=self.request.user, target=target
        )


class SchoolViewSet(PermissionRequiredMixin, ListRetrieveViewSet):
    """School List and Retrieve Functionality"""

    summaries = {
        "list": "Schools List",
        "retrieve": "Schools Retrieve",
    }

    queryset = models.School.active_objects.all()
    pagination_class = PageNumberPagination

    serializer_class = serializers.SchoolSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["is_active"]

    search_fields = ["name"]
    ordering_fields = ["name"]
    ordering = ["name"]

    permission_classes = [IsAuthenticated, IsAdminUser]
    permission = ["core_accounts.view_school"]
    permissions = {
        "list": ["core_accounts.view_school"],
        "retrieve": ["core_accounts.view_school"],
    }


class DepartmentViewSet(PermissionRequiredMixin, ModelViewSet):
    queryset = models.Department.active_objects.all()
    pagination_class = PageNumberPagination

    serializer_class = serializers.DepartmentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["school", "division_group"]

    search_fields = ["name", "code"]
    ordering_fields = ["name", "code"]
    ordering = ["name", "code"]

    permission_classes = [IsAuthenticated, IsAdminUser]
    permission = ["core_accounts.view_department"]
    permissions = {
        "list": ["core_accounts.view_department"],
        "retrieve": ["core_accounts.view_department"],
    }


class FacultyListRetrieveViewSet(
    ViewSetSerializerClassMixin, PermissionRequiredMixin, ModelViewSet
):
    queryset = selectors.faculty_list_get()
    pagination_class = PageNumberPagination

    serializer_class = serializers.FacultyBaseSerializer
    serializer_classes = {
        "list": serializers.FacultyBaseSerializer,
        "retrieve": serializers.FacultyDetailSerializer,
    }
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["emp_id", "first_name", "last_name", "category"]

    search_fields = [
        "emp_id",
        "first_name",
        "last_name",
    ]
    ordering_fields = ["-created_at"]
    ordering = ["-created_at"]

    permission_classes = [IsAuthenticated, IsAdminUser]
    permission = ["core_accounts.view_personnel"]
    permissions = {
        "list": ["core_accounts.view_personnel"],
        "retrieve": [
            "core_accounts.view_personnel",
            "core_cms.view_class",
            "core_cms.view_classschedule",
        ],
    }


class AcademicYearCurrentAPIView(RetrieveAPIView):
    """Retrieves the current academic year"""

    queryset = models.AcademicYear.objects.all()
    serializer_class = serializers.AcademicYearCurrentRetrieveSerializer

    permission_classes = [IsAuthenticated]

    def get_object(self):
        obj = selectors.current_academic_year_get()
        self.check_object_permissions(self.request, obj)
        return obj


class SemesterListRetrieveViewset(ListRetrieveViewSet):
    summaries = {
        "list": "Semesters List",
        "retrieve": "Semesters Retrieve",
    }
    queryset = models.Semester.objects.all()
    serializer_class = serializers.SemesterSerializer

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["academic_year"]
    ordering_fields = ["order"]
    ordering = ["order"]

    permission_classes = [IsAuthenticated, IsAdminUser]


@extend_schema(tags=[Tags.ACADEMIC_YEARS])
class AcademicYearListRetrieveViewset(ListRetrieveViewSet):
    summaries = {
        "list": "Academic Years List",
        "retrieve": "Academic Years Retrieve",
    }
    queryset = models.AcademicYear.objects.all()
    serializer_class = serializers.AcademicYearSerializer

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["year_start"]
    ordering_fields = ["year_start"]
    ordering = ["year_start"]

    permission_classes = [IsAuthenticated, IsAdminUser]


@extend_schema(tags=[Tags.SEMESTERS])
class SemesterUpcomingAPIView(RetrieveAPIView):
    """Retrieves the upcoming semester"""

    queryset = models.Semester.objects.all()
    serializer_class = serializers.SemesterUpcomingRetrieveSerializer

    permission_classes = [IsAuthenticated]

    def get_object(self):
        obj = selectors.next_semester_get()
        self.check_object_permissions(self.request, obj)
        return obj


@extend_schema(tags=[Tags.STAFFS])
class PersonnelProfileApi(RetrieveAPIView):
    """Retrieve profile of authenticated personnel/staff"""

    queryset = models.User.objects.filter(is_staff=True)
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = serializers.PersonnelProfileRetrieveSerializer

    def get_object(self):
        return self.request.user


@extend_schema(tags=[Tags.SEMESTERS])
class SemesterPreviousAPIView(RetrieveAPIView):
    """Retrieves the previous semester"""

    queryset = models.Semester.objects.all()
    serializer_class = serializers.SemesterPreviousRetrieveSerializer

    permission_classes = [IsAuthenticated]

    def get_object(self):
        obj = selectors.previous_semester_get()
        self.check_object_permissions(self.request, obj)
        return obj
