from decimal import Decimal

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import serializers as rest_serializers
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import ModelSerializer
from rest_framework.viewsets import ModelViewSet

from config.settings.openapi import Tags
from university.core.accounts.filters import SchoolFilter, SchoolFilterSet
from university.core.accounts.models import (
    AcademicYear,
    Department,
    Personnel,
    Semester,
)
from university.core.accounts.selectors import current_semester_get, user_schools_get
from university.framework.pagination import PageNumberPagination
from university.framework.permissions import IsAdminUser
from university.framework.serializers import InlineSerializerMixin
from university.framework.views import (
    ListRetrieveViewSet,
    PermissionRequiredMixin,
    ViewSetSerializerClassMixin,
)
from rest_framework.generics import (
    ListAPIView,
    RetrieveUpdateDestroyAPIView,
    CreateAPIView,
)

from . import models, serializers, services


class RoomViewSet(PermissionRequiredMixin, ModelViewSet):
    school_field = "school"

    class Filter(SchoolFilterSet):
        class Meta:
            model = models.Room
            fields = ["school", "name", "number"]

    Filter.school_field = school_field

    queryset = models.Room.active_objects.all()
    pagination_class = PageNumberPagination

    serializer_class = serializers.RoomSerializer
    filter_backends = [SchoolFilter, DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = Filter

    search_fields = ["name", "number"]
    ordering_fields = ["number", "wing", "floor_no"]
    ordering = ["number", "wing", "floor_no"]

    permission_classes = [IsAuthenticated, IsAdminUser]
    permission = ["core_cms.view_room"]
    permissions = {
        "create": ["core_cms.add_room"],
        "list": ["core_cms.view_room"],
        "retrieve": ["core_cms.view_room"],
        "update": ["core_cms.change_room"],
        "partial_update": ["core_cms.change_room"],
        "destroy": ["core_cms.delete_room"],
    }

    def perform_destroy(self, instance):
        services.room_delete(room=instance)


class CurriculumViewset(
    ViewSetSerializerClassMixin, PermissionRequiredMixin, ModelViewSet
):
    school_field = "course__school"

    class Filter(SchoolFilterSet):
        class Meta:
            model = models.Curriculum
            fields = ["course__school", "course__name"]

    Filter.school_field = school_field

    pagination_class = PageNumberPagination

    filter_backends = [SchoolFilter, DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = Filter

    search_fields = ["ref_id", "course__name", "effective_start_year"]

    ordering_fields = ["id"]
    ordering = ["id"]

    serializer_class = serializers.CurriculumSerializer
    serializer_classes = {
        "retrieve": serializers.CurriculumRetrieveSerializer,
        "create": serializers.CurriculumCreateUpdateSerializer,
        "update": serializers.CurriculumCreateUpdateSerializer,
        "partial_update": serializers.CurriculumCreateUpdateSerializer,
    }

    permission_classes = [IsAuthenticated, IsAdminUser]
    permission = ["core_cms.view_curriculum"]
    permissions = {
        "create": ["core_cms.add_curriculum"],
        "list": ["core_cms.view_curriculum"],
        "retrieve": [
            "core_cms.view_curriculum",
            "core_cms.view_curriculumperiod",
            "core_cms.view_curriculumsubject",
        ],
        "update": ["core_cms.change_curriculum"],
        "partial_update": ["core_cms.change_curriculum"],
        "destroy": ["core_cms.delete_curriculum"],
    }

    def get_queryset(self):
        return models.Curriculum.active_objects.select_related(
            "course"
        ).prefetch_related(
            "curriculum_periods",
            "curriculum_periods__curriculum_subjects",
            "curriculum_periods__curriculum_subjects__subject",
            "curriculum_periods__curriculum_subjects__requisites",
        )


class CurriculumPeriodViewset(ModelViewSet):
    pagination_class = PageNumberPagination

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["semester", "year_level", "curriculum"]

    search_fields = ["curriculum", "semester", "year_level"]

    ordering_fields = ["semester", "year_level"]
    ordering = ["semester", "year_level"]

    serializer_class = serializers.CurriculumPeriodListRetrieveSerializer

    permission_classes = [IsAuthenticated, IsAdminUser]
    permission = ["core.view_curriculum"]
    permissions = {
        "create": ["core.add_curriculum"],
        "list": ["core.view_curriculum"],
        "retrieve": ["core.view_curriculum"],
        "update": ["core.change_curriculum"],
        "partial_update": ["core.change_curriculum"],
        "destroy": ["core.delete_curriculum"],
    }

    def get_queryset(self):
        return models.CurriculumPeriod.active_objects.select_related(
            "curriculum", "curriculum__course"
        ).prefetch_related(
            "curriculum_subjects",
            "curriculum_subjects__subject",
            "curriculum_subjects__requisites",
            "curriculum_subjects__requisites__requisite_subject",
        )


class ClassViewset(InlineSerializerMixin, PermissionRequiredMixin, ModelViewSet):
    school_field = "course__school"

    class Filter(SchoolFilterSet):
        class Meta:
            model = models.Class
            fields = [
                "class_code",
                "subject__course_code",
                "subject__course_number",
                "is_dissolved",
                "is_intercollegiate",
                "class_code",
                "is_dissolved",
                "course",
                "semester__term",
                "year_level",
                "semester__academic_year__year_start",
                "semester__academic_year__year_end",
            ]

    Filter.school_field = school_field

    pagination_class = PageNumberPagination

    filter_backends = [SchoolFilter, DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = Filter

    search_fields = [
        "subject__course_number",
        "subject__descriptive_title",
        "class_code",
    ]
    ordering_fields = ["-created_at"]
    ordering = ["-created_at"]

    permission_classes = [IsAuthenticated, IsAdminUser]
    permission = ["core_cms.view_class", "core_cms.view_classschedule"]
    permissions = {
        "create": ["core_cms.add_class"],
        "list": ["core_cms.view_class", "core_cms.view_classschedule"],
        "retrieve": ["core_cms.view_class", "core_cms.view_classschedule"],
        "update": ["core_cms.change_class"],
        "partial_update": ["core_cms.change_class"],
        "destroy": ["core_cms.delete_class"],
    }

    def list_serializer_class(self):
        academic_year_serializer = self.inline_serializer_class(
            fields={},
            meta_model=AcademicYear,
            meta_fields=("id", "year_start", "year_end", "date_start", "date_end"),
        )

        semester_serializer = self.inline_serializer_class(
            fields={"academic_year": academic_year_serializer()},
            meta_model=Semester,
            meta_fields=(
                "academic_year",
                "id",
                "term",
                "date_start",
                "date_end",
                "order",
            ),
        )

        instructor_serializer = self.inline_serializer_class(
            fields={},
            meta_model=Personnel,
            meta_fields=("first_name", "last_name"),
        )

        subject_serializer = self.inline_serializer_class(
            fields={},
            meta_model=models.Subject,
            meta_fields=(
                "ref_id",
                "course_code",
                "course_number",
                "descriptive_code",
                "descriptive_title",
            ),
        )

        class OutputSerializer(ModelSerializer):
            semester = semester_serializer()
            instructor = rest_serializers.SerializerMethodField()
            total_students_enrolled = rest_serializers.SerializerMethodField()
            subject = rest_serializers.SerializerMethodField()
            units = rest_serializers.SerializerMethodField()

            class Meta:
                model = models.Class
                fields = "__all__"

            def get_instructor(self, obj) -> instructor_serializer:
                return instructor_serializer(obj.instructor).data

            def get_total_students_enrolled(self, obj) -> Decimal:
                return obj.get_total_students_enrolled()

            def get_subject(self, obj) -> subject_serializer:
                return subject_serializer(obj.subject).data

            def get_units(self, obj) -> Decimal:
                return obj.subject.units if obj.subject else 0

        return OutputSerializer

    def get_queryset(self):
        return models.Class.objects.select_related(
            "instructor", "subject", "semester", "course"
        )

    def get_serializer_class(self):
        serializer_class = self.list_serializer_class()
        serializer_classes = {
            "retrieve": serializers.ClassSerializer,
            "list": self.list_serializer_class(),
        }
        return serializer_classes.get(self.action, serializer_class)

    def perform_destroy(self, instance):
        services.class_delete(klass=instance)


class SubjectViewset(PermissionRequiredMixin, ModelViewSet):
    school_field = "school"

    class Filter(SchoolFilterSet):
        class Meta:
            model = models.Subject
            fields = [
                "ref_id",
                "course_code",
                "descriptive_code",
                "is_professional_subject",
                "is_lab_subject",
                "school",
            ]

    Filter.school_field = school_field

    queryset = models.Subject.objects.all()
    pagination_class = PageNumberPagination

    serializer_class = serializers.SubjectSerializer
    filter_backends = [SchoolFilter, DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = Filter
    search_fields = [
        "ref_id",
        "course_code",
        "course_number",
        "descriptive_code",
        "descriptive_title",
    ]
    ordering_fields = ["ref_id", "course_code"]
    ordering = ["ref_id", "course_code"]

    permission_classes = [IsAuthenticated, IsAdminUser]
    permission = ["core_cms.view_subject"]
    permissions = {
        "create": ["core_cms.add_subject"],
        "list": ["core_cms.view_subject"],
        "retrieve": ["core_cms.view_subject"],
        "update": ["core_cms.change_subject"],
        "partial_update": ["core_cms.change_subject"],
        "destroy": ["core_cms.delete_subject"],
    }

    def perform_destroy(self, instance):
        services.subject_delete(subject=instance)


class CourseListRetrieveAPIView(PermissionRequiredMixin, ListRetrieveViewSet):
    """Corse List and Retrieve Functionality"""

    school_field = "school"

    class Filter(SchoolFilterSet):
        class Meta:
            model = models.Course
            fields = [
                "code",
                "sub_code",
                "name",
            ]

    Filter.school_field = school_field

    summaries = {
        "list": "Courses List",
        "retrieve": "Courses Retrieve",
    }

    queryset = models.Course.active_objects.all()

    pagination_class = PageNumberPagination
    serializer_class = serializers.CourseSerializer

    filter_backends = [SchoolFilter, DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = Filter

    search_fields = ["code", "sub_code", "sub_code"]
    ordering_fields = ["code", "sub_code", "sub_code"]
    ordering = ["code", "sub_code", "sub_code"]

    permission_classes = [IsAuthenticated, IsAdminUser]
    permission = ["core_cms.view_course"]
    permissions = {
        "list": ["core_cms.view_course"],
        "retrieve": ["core_cms.view_course"],
    }


class BuildingListRetrieveAPIView(PermissionRequiredMixin, ListRetrieveViewSet):
    """Building List and Retrieve Functionality"""

    summaries = {
        "list": "Buildings List",
        "retrieve": "Buildings Retrieve",
    }

    pagination_class = PageNumberPagination
    serializer_class = serializers.BuildingSerializer

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        "ref_id": ["icontains"],
        "sub_code": ["icontains"],
        "name": ["icontains"],
    }

    search_fields = ["ref_id", "sub_code", "name"]
    ordering_fields = ["ref_id", "sub_code", "name"]
    ordering = ["-created_at"]

    permission_classes = [IsAuthenticated, IsAdminUser]
    permission = ["core_cms.view_building"]
    permissions = {
        "list": ["core_cms.view_building"],
        "retrieve": ["core_cms.view_building"],
    }

    def get_queryset(self):
        return models.Building.objects.prefetch_related("schools")


class FeeListRetrieveAPIView(PermissionRequiredMixin, ListRetrieveViewSet):
    """Fee List and Retrieve Functionality"""

    summaries = {
        "list": "Fees List",
        "retrieve": "Fees Retrieve",
    }

    queryset = models.Fee.active_objects.all()

    pagination_class = PageNumberPagination
    serializer_class = serializers.FeeSerializer

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        "code": ["icontains"],
        "name": ["icontains"],
        "type": ["exact"],
        "academic_year__year_start": ["exact"],
        "academic_year__year_end": ["exact"],
    }
    search_fields = [
        "code",
        "name",
        "type",
        "academic_year__year_start",
        "academic_year__year_end",
    ]
    ordering_fields = [
        "code",
        "name",
        "type",
        "academic_year__year_start",
        "academic_year__year_end",
    ]
    ordering = ["-academic_year__year_start"]

    permission_classes = [IsAuthenticated, IsAdminUser]
    permission = ["core_cms.view_fee"]
    permissions = {
        "list": ["core_cms.view_fee"],
        "retrieve": ["core_cms.view_fee"],
    }


class FeeSpecificationListRetrieveAPIView(PermissionRequiredMixin, ListRetrieveViewSet):
    """Fee Specification List and Retrieve Functionality"""

    summaries = {
        "list": "Fee Specifications List",
        "retrieve": "Fee Specifications Retrieve",
    }

    pagination_class = PageNumberPagination
    serializer_class = serializers.FeeSpecificationPolymorphicSerializer

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        "school": ["exact"],
        "subject": ["exact"],
    }

    search_fields = ["code", "description"]
    ordering_fields = ["code", "description"]
    ordering = ["code", "description"]
    ordering = ["-academic_year__year_start"]

    permission_classes = [IsAuthenticated, IsAdminUser]
    permission = ["core_cms.view_fee", "core_cms.view_feespecification"]
    permissions = {
        "list": ["core_cms.view_fee", "core_cms.view_feespecification"],
        "retrieve": ["core_cms.view_fee", "core_cms.view_feespecification"],
    }

    def get_queryset(self):
        return models.FeeSpecification.objects.select_related(
            "school", "subject", "academic_year"
        ).prefetch_related("fees")


class RoomClassificationListRetrieveAPIView(
    PermissionRequiredMixin, ListRetrieveViewSet
):
    """Room Classification List and Retrieve Functionality"""

    summaries = {
        "list": "Room Classification List",
        "retrieve": "Room Classification Retrieve",
    }

    queryset = models.Classification.objects.all()
    pagination_class = PageNumberPagination
    serializer_class = serializers.ClassificationSerializer

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        "name": ["icontains"],
    }
    search_fields = ["name"]
    ordering_fields = ["id"]
    ordering = ["id"]

    permission_classes = [IsAuthenticated, IsAdminUser]
    permission = ["core_cms.view_classification"]
    permissions = {
        "list": ["core_cms.view_classification"],
        "retrieve": ["core_cms.view_classification"],
    }


class DiscountListRetrieveAPIView(
    PermissionRequiredMixin, InlineSerializerMixin, ListRetrieveViewSet
):
    """Discount List and Retrieve Functionality"""

    summaries = {
        "list": "Discount List",
        "retrieve": "Discount Retrieve",
    }

    queryset = models.Discount.objects.all()
    pagination_class = PageNumberPagination

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        "name": ["icontains"],
    }
    search_fields = ["name"]
    ordering_fields = ["id"]
    ordering = ["id"]

    permission_classes = [IsAuthenticated, IsAdminUser]
    permission = ["core_cms.view_discount"]
    permissions = {
        "list": ["core_cms.view_discount"],
        "retrieve": ["core_cms.view_discount", "core_cms.view_fee"],
    }

    def get_serializer_class(self):
        class OutputSerializer(ModelSerializer):
            fee_exemptions = self.inline_serializer(
                model=models.Fee,
                fields={},
                meta_fields=("id", "code", "name", "description", "type", "amount"),
                many=True,
            )
            department = self.inline_serializer(
                model=Department,
                fields={},
                meta_fields=("id", "code", "name"),
            )

            class Meta:
                model = models.Discount
                fields = "__all__"

        return OutputSerializer


class PersonnelClassScheduleListAPIView(ListAPIView):
    """List all the current schedules of the authenticated admin user"""

    school_field = "klass__subject__school"

    class Filter(SchoolFilterSet):
        class Meta:
            model = models.ClassSchedule
            fields = []

    Filter.school_field = school_field

    pagination_class = PageNumberPagination
    serializer_class = serializers.PersonnelClassScheduleSerializer

    filter_backends = [SchoolFilter, OrderingFilter]
    filterset_class = Filter

    ordering_fields = ["-created_at"]
    ordering = ["-created_at"]

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        return (
            models.ClassSchedule.objects.filter(
                klass__instructor__user=self.request.user,
                klass__semester=current_semester_get(),
            )
            .select_related("klass", "room")
            .prefetch_related(
                "klass__course",
                "klass__instructor",
                "klass__subject",
                "klass__semester",
            )
        )


@extend_schema(tags=[Tags.DASHBOARDS])
class OpenClassPerSchoolListAPIView(ListAPIView):
    """List all schools with its corresponding number of open classes"""

    serializer_class = serializers.OpenClassPerSchoolSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        return user_schools_get(user=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["year_level"] = self.request.GET.get("year_level", None)
        return context


@extend_schema(tags=[Tags.DASHBOARDS])
class OpenClassEnrolleePerCourseListAPIView(ListAPIView):
    """List all courses with its corresponding number of open classes and enrollees"""

    pagination_class = PageNumberPagination
    serializer_class = serializers.OpenClassEnrolleePerCourseSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["code", "name"]

    search_fields = ["code", "name"]

    def get_queryset(self):
        schools = user_schools_get(user=self.request.user)
        return models.Course.objects.filter(school__in=schools)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["year_level"] = self.request.GET.get("year_level", None)
        return context


@extend_schema(tags=[Tags.DASHBOARDS])
class AnnouncementsListAPIView(ListAPIView):
    """List of General Announcements"""

    queryset = models.Announcement.objects.all()
    serializer_class = serializers.AnnouncementsSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    class Meta:
        model = models.Announcement
        fields = ["start_date", "end_date", "subject", "content"]


class AnnouncementsListCreateAPIView(CreateAPIView):
    class OutputSerializer(rest_serializers.ModelSerializer):
        class Meta:
            model = models.Announcement
            fields = ["start_date", "end_date", "subject", "content"]

    serializer_class = OutputSerializer
    queryset = models.Announcement.objects.all()
    permission_classes = [IsAuthenticated, IsAdminUser]


class AnnouncementsUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    class InputSerializer(rest_serializers.ModelSerializer):
        class Meta:
            model = models.Announcement
            fields = ["start_date", "end_date", "subject", "content"]

    serializer_class = InputSerializer
    queryset = models.Announcement.objects.all()
    permission_classes = [IsAuthenticated, IsAdminUser]

    http_method_names = RetrieveUpdateDestroyAPIView.http_method_names.copy()
    http_method_names.remove("get")

    def perform_destroy(self, instance):
        instance.soft_delete()


@extend_schema(tags=[Tags.DASHBOARDS])
class ClassGradeStatePerSchoolListAPIView(ListAPIView):
    """List all schools with its corresponding class grades states count"""

    serializer_class = serializers.ClassGradeStatePerSchoolSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        return user_schools_get(user=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["year_level"] = self.request.GET.get("year_level", None)
        return context
