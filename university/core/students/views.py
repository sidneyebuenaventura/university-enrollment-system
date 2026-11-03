from django.db import transaction as db_transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import exceptions, status
from rest_framework import serializers as rest_serializers
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import (
    CreateAPIView,
    GenericAPIView,
    ListAPIView,
    RetrieveAPIView,
    RetrieveUpdateAPIView,
)
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import Serializer as EmptySerializer

from config.settings.openapi import Tags
from university.core import events
from university.core.accounts.filters import SchoolFilter, SchoolFilterSet
from university.core.accounts.selectors import user_schools_get
from university.core.cms.models import Class, Curriculum
from university.framework.events import event_publisher
from university.framework.pagination import PageNumberPagination
from university.framework.permissions import IsAdminUser, IsStudentUser
from university.framework.serializers import InlineSerializerMixin
from university.framework.views import (
    ApiSerializerClassMixin,
    ListRetrieveUpdateViewSet,
    ListRetrieveViewSet,
    PermissionRequiredMixin,
    ViewSetSerializerClassMixin,
)

from . import selectors, serializers, services
from .models import (
    AddSubjectRequest,
    ChangeScheduleRequest,
    EnrolledClass,
    EnrolledClassGrade,
    Enrollment,
    GeneralWeightedAverageSheet,
    GradeFields,
    GradeSheet,
    OpenClassRequest,
    Student,
    WithdrawalRequest,
)


@extend_schema(tags=[Tags.STUDENT_PROFILE])
class StudentProfileApi(ApiSerializerClassMixin, RetrieveUpdateAPIView):
    summaries = {
        "get": "Retrieve profile of authenticated student",
        "put": "Update profile of authenticated student",
        "patch": "Partial update of authenticated student",
    }

    queryset = Student.objects.filter(type=Student.Types.STUDENT)
    permission_classes = [IsAuthenticated, IsStudentUser]

    serializer_class = serializers.StudentProfileRetrieveSerializer
    serializer_classes = {
        "put": serializers.StudentProfileUpdateSerializer,
        "patch": serializers.StudentProfileUpdateSerializer,
    }

    def get_object(self):
        return self.request.user.student


class StudentListRetrieveAPIView(ViewSetSerializerClassMixin, ListRetrieveViewSet):
    """Student List and Retrieve Functionality"""

    summaries = {
        "list": "Students List",
        "retrieve": "Students Retrieve",
    }

    queryset = Student.objects.filter(type=Student.Types.STUDENT)

    pagination_class = PageNumberPagination
    permission_classes = [IsAuthenticated, IsAdminUser]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        "id_number": ["icontains"],
        "first_name": ["icontains"],
        "last_name": ["icontains"],
    }
    search_fields = ["id_number", "first_name", "last_name"]
    ordering_fields = ["id_number", "first_name", "last_name"]
    ordering = ["first_name", "last_name"]

    serializer_class = serializers.StudentListSerializer
    serializer_classes = {
        "list": serializers.StudentListSerializer,
        "retrieve": serializers.StudentRetrieveSerializer,
    }


@extend_schema(tags=[Tags.STUDENT_ENROLLMENT])
class StudentEnrollmentOngoingAPIView(RetrieveUpdateAPIView):
    """Retrieves ongoing enrollment for the upcoming semester"""

    summaries = {
        "patch": "Update student's enrollment information",
        "retrieve": "Retrieves ongoing enrollment for the upcoming semester",
    }

    queryset = Enrollment.objects.all()
    serializer_class = serializers.EnrollmentRetrieveSerializer
    permission_classes = [IsAuthenticated, IsStudentUser]

    serializer_classes_by_step = {
        Enrollment.Steps.INFORMATION.value: serializers.EnrollmentInformationSerializer,
        Enrollment.Steps.DISCOUNTS.value: serializers.EnrollmentDiscountSerializer,
        Enrollment.Steps.SUBJECTS.value: serializers.EnrolledClassSerializer,
    }

    # Disable PUT method, enrollment updates are by Steps
    # so we should update the record using PATCH.
    http_method_names = RetrieveUpdateAPIView.http_method_names.copy()
    http_method_names.remove("put")

    def get_object(self):
        obj = selectors.enrollment_get_ongoing(
            user=self.request.user, raise_exception=True
        )
        # May raise a permission denied
        self.check_object_permissions(self.request, obj)
        return obj

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            default = serializers.EnrollmentInformationSerializer
            step = str(self.request.data.get("step"))
            return self.serializer_classes_by_step.get(step) or default

        return self.serializer_class

    def perform_update(self, serializer):
        services.enrollment_update(
            enrollment=serializer.instance, data=serializer.validated_data
        )


@extend_schema(tags=[Tags.STUDENT_ENROLLMENT])
class StudentEnrollmentCreateAPIView(CreateAPIView):
    """Create Student Enrollment"""

    queryset = Enrollment.objects.all()
    serializer_class = serializers.EnrollmentInformationSerializer
    permission_classes = [IsAuthenticated, IsStudentUser]

    def perform_create(self, serializer):
        serializer.instance = services.enrollment_create(
            student=self.request.user.student, data=serializer.validated_data
        )


@extend_schema(tags=[Tags.STUDENTS])
class StudentClassGradeListAPIView(InlineSerializerMixin, ListAPIView):
    """List all enrollment with grades of a student"""

    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = serializers.StudentClassGradeListSerializer

    filter_backends = [OrderingFilter]
    ordering_fields = ["year_level", "semester"]
    ordering = ["year_level", "semester"]

    def get_queryset(self):
        student = get_object_or_404(Student, pk=self.kwargs.get("pk"))
        return (
            Enrollment.objects.select_related("semester")
            .prefetch_related(
                "enrolled_classes__klass__subject",
                "enrolled_classes__grades",
            )
            .filter(student=student)
        )


@extend_schema(tags=[Tags.STUDENT_ENROLLMENT])
class StudentEnrollmentListAPIView(InlineSerializerMixin, ListAPIView):
    """List Enrollment of authenticated student"""

    permission_classes = [IsAuthenticated, IsStudentUser]
    serializer_class = serializers.StudentEnrollmentListSerializer

    filter_backends = [OrderingFilter]
    ordering_fields = ["year_level", "semester__order"]
    ordering = ["year_level", "semester__order"]

    def get_queryset(self):
        student = self.request.user.student
        return (
            Enrollment.objects.select_related("semester")
            .prefetch_related(
                "enrolled_classes__klass__subject",
                "enrolled_classes__equivalent_subject",
                "enrolled_classes__klass__class_schedules",
            )
            .filter(student=student)
        )


@extend_schema(tags=[Tags.STUDENT_CLASSES])
class StudentClassListAPIView(InlineSerializerMixin, ListAPIView):
    """List Classes of authenticated student for the current semester"""

    permission_classes = [IsAuthenticated, IsStudentUser]
    serializer_class = serializers.StudentClassListSerializer

    def get_queryset(self):
        return selectors.student_class_list(user=self.request.user)


@extend_schema(tags=[Tags.CLASSES])
class EnrolledClassGradeListAPIView(InlineSerializerMixin, ListAPIView):
    """List all grades within a class"""

    pagination_class = PageNumberPagination
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = serializers.EnrolledClassGradeListSerializer

    filter_backends = [OrderingFilter]
    ordering_fields = ["enrollment__student__last_name"]
    ordering = ["enrollment__student__last_name"]

    def get_queryset(self):
        klass = get_object_or_404(Class, pk=self.kwargs.get("pk"))
        return (
            EnrolledClass.objects.select_related("enrollment")
            .prefetch_related(
                "enrollment__student",
                "klass__subject",
            )
            .filter(klass=klass)
        )


@extend_schema(tags=[Tags.GRADE_SHEETS])
class GradeSheetApi(InlineSerializerMixin, CreateAPIView):
    class InputSerializer(rest_serializers.ModelSerializer):
        class Meta:
            model = GradeSheet
            fields = ("file_id", "klass", "file")
            read_only_fields = ("file_id",)

    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = InputSerializer

    def get_queryset(self):
        klass = get_object_or_404(Class, pk=self.kwargs.get("pk"))
        return GradeSheet.objects.filter(klass=klass)

    def perform_create(self, serializer):
        grade_sheet = GradeSheet.objects.create(
            klass=serializer.validated_data.get("klass"),
            file=serializer.validated_data.get("file"),
        )
        grade_sheet.generate_id()
        serializer.instance = grade_sheet
        event_publisher.generic(events.GRADE_SHEET_CREATED, grade_sheet)


class GradeSheetDetailApi(RetrieveAPIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = serializers.GradeSheetDetailApiSerializer
    queryset = GradeSheet.objects.all()
    lookup_field = "file_id"


class GradeSheetDraftApi(GenericAPIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = EmptySerializer
    queryset = GradeSheet.objects.all()

    def post(self, request, file_id):
        grade_sheet = get_object_or_404(GradeSheet, file_id=file_id)

        if grade_sheet.status != GradeSheet.Statuses.COMPLETED:
            raise exceptions.APIException("Invalid grade sheet")

        event_publisher.generic(events.GRADE_SHEET_DRAFTED, grade_sheet)
        return Response()


class GradeSheetSubmitApi(GenericAPIView):
    class InputSerializer(rest_serializers.Serializer):
        prelim_grade = rest_serializers.BooleanField(default=False)
        midterm_grade = rest_serializers.BooleanField(default=False)
        tentative_final_grade = rest_serializers.BooleanField(default=False)
        final_grade = rest_serializers.BooleanField(default=False)

    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = InputSerializer
    queryset = GradeSheet.objects.all()

    def post(self, request, file_id):
        grade_sheet = get_object_or_404(GradeSheet, file_id=file_id)

        if grade_sheet.status != GradeSheet.Statuses.COMPLETED:
            raise exceptions.APIException("Invalid grade sheet")

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        fields = []

        for field in GradeFields.values:
            if serializer.validated_data.get(field):
                fields.append(field)

        event_publisher.generic(
            events.GRADE_SHEET_SUBMITTED, grade_sheet, fields=fields
        )
        return Response()


@extend_schema(tags=[Tags.STUDENT_ENROLLMENT])
class PreEnrollmentListAPIView(ListAPIView):
    """List all preenrollments"""

    pagination_class = PageNumberPagination
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = serializers.EnrollmentStudentSerializer

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        "student__id_number": ["icontains"],
        "student__first_name": ["icontains"],
        "student__last_name": ["icontains"],
        "status": ["in"],
        "enrollmentstatus__is_for_manual_tagging": ["exact"],
        "enrollmentstatus__block_status": ["in"],
        "enrollmentstatus__remark_code": ["in"],
    }
    search_fields = [
        "student__id_number",
        "student__first_name",
        "student__last_name",
        "status",
        "is_for_manual_tagging",
    ]
    ordering_fields = [
        "student__id_number",
        "student__first_name",
        "student__last_name",
    ]
    ordering = ["student__first_name", "student__last_name"]

    def get_queryset(self):
        return selectors.next_semester_enrollment_list()


@extend_schema(tags=[Tags.STUDENT_ENROLLMENT])
class EnrollmentRemarkUpdateAPIView(GenericAPIView):
    """Pre-Enrollment Remark Status Bulk update"""

    serializer_class = serializers.EnrollmentRemarkUpdateSerializer

    @db_transaction.atomic
    def post(self, request, *args, **kwargs):
        services.enrollment_remark_update(data=request.data)
        return HttpResponse(status=204)


@extend_schema(tags=[Tags.STUDENT_ENROLLMENT])
class EnrollmentStatusUpdateAPIView(GenericAPIView):
    """Pre-Enrollment Status Bulk update"""

    serializer_class = serializers.EnrollmentStatusUpdateSerializer

    @db_transaction.atomic
    def post(self, request, *args, **kwargs):
        services.enrollment_status_update(data=request.data)
        return HttpResponse(status=204)


@extend_schema(tags=[Tags.STUDENT_ENROLLMENT])
class StudentEnrollmentActiveAPIView(InlineSerializerMixin, RetrieveAPIView):
    """Retrieve active enrollment for the current academic year and semester"""

    permission_classes = [IsAuthenticated, IsStudentUser]
    serializer_class = serializers.EnrollmentActiveRetrieveSerializer

    def get_queryset(self):
        return Enrollment.objects.filter(student=self.request.user.student)

    def get_object(self):
        enrollment = selectors.enrollment_get_active(
            user=self.request.user, raise_exception=True
        )
        self.check_object_permissions(self.request, enrollment)
        return enrollment if enrollment else None


@extend_schema(tags=[Tags.STUDENT_PROFILE])
class StudentCurriculumRetrieveAPIView(InlineSerializerMixin, RetrieveAPIView):
    """Retrieve curriculum details of authenticated student"""

    permission_classes = [IsAuthenticated, IsStudentUser]
    serializer_class = serializers.StudentCurriculumRetrieveSerializer

    def get_queryset(self):
        return (
            Curriculum.objects.filter(course=self.request.user.student.course)
            .select_related("curriculum_periods", "course")
            .prefetch_related(
                "curriculum_subjects",
                "curriculum_subjects__subject",
                "curriculum_subjects__requisites",
            )
        )

    def get_object(self):
        return self.request.user.student.curriculum

    def get_serializer_context(self):
        context = super().get_serializer_context()
        student = self.request.user.student
        enrolled_classes = student.enrolled_classes.filter(
            status=EnrolledClass.Statuses.ENROLLED, curriculum_subject__isnull=False
        )
        curr_subj_ids = [
            enrolled_class.curriculum_subject.id for enrolled_class in enrolled_classes
        ]

        passed_curr_subj_ids = [
            enrolled_class.curriculum_subject.id
            for enrolled_class in enrolled_classes.filter(
                grades__status=EnrolledClassGrade.Statuses.PASSED
            )
        ]
        context["curr_subj_ids"] = curr_subj_ids
        context["passed_curr_subj_ids"] = passed_curr_subj_ids
        context["student"] = self.request.user.student
        return context


@extend_schema(tags=[Tags.STUDENT_GRADES])
class StudentEnrollmentGradeListAPIView(InlineSerializerMixin, ListAPIView):
    """List grade record per enrollment of authenticated student"""

    permission_classes = [IsAuthenticated, IsStudentUser]
    serializer_class = serializers.StudentEnrollmentGradeListSerializer

    filter_backends = [OrderingFilter]
    ordering_fields = ["-year_level", "-semester__order"]
    ordering = ["-year_level", "-semester__order"]

    def get_queryset(self):
        student = self.request.user.student
        return (
            Enrollment.objects.select_related("semester")
            .prefetch_related(
                "enrolled_classes__klass__subject",
                "enrolled_classes__equivalent_subject",
                "semester__academic_year",
            )
            .filter(student=student)
        )


@extend_schema(tags=[Tags.DASHBOARDS])
class FailedStudentPerSchoolListAPIView(ListAPIView):
    """List all schools with its corresponding number of failed students from previous term"""

    serializer_class = serializers.FailedStudentPerSchoolSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        return user_schools_get(user=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["year_level"] = self.request.GET.get("year_level", None)
        return context


@extend_schema(tags=[Tags.DASHBOARDS])
class InterviewedFailedStudentPerSchoolListAPIView(ListAPIView):
    """List all schools with its corresponding number of interviewed failed students from previous term"""

    serializer_class = serializers.InterviewedFailedStudentPerSchoolSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        return user_schools_get(user=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["year_level"] = self.request.GET.get("year_level", None)
        return context


@extend_schema(tags=[Tags.DASHBOARDS])
class EnrolleePerSchoolListAPIView(ListAPIView):
    """List all schools with its corresponding number of enrollees"""

    serializer_class = serializers.EnrolleesPerSchoolSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        return user_schools_get(user=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["year_level"] = self.request.GET.get("year_level", None)
        return context


@extend_schema(tags=[Tags.DASHBOARDS])
class EnrolleeScholarPerSchoolListAPIView(ListAPIView):
    """List all schools with its corresponding number of regular and scholar enrollees"""

    serializer_class = serializers.EnrolleeScholarPerSchoolSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        return user_schools_get(user=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["year_level"] = self.request.GET.get("year_level", None)
        return context


@extend_schema(tags=[Tags.STUDENT_GRADES])
class EnrollmentGWAUploadAPI(CreateAPIView):
    """Upload student enrollment GWA"""

    queryset = GeneralWeightedAverageSheet.objects.all()
    serializer_class = serializers.EnrollmentGWAUploadSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    parser_classes = [MultiPartParser]

    def perform_create(self, serializer):
        gwa_sheet = services.gwa_sheet_create(
            file=serializer.validated_data.get("file")
        )
        serializer.instance = gwa_sheet


@extend_schema(tags=[Tags.DASHBOARDS])
class EnrolleesPerDayPerSchoolListAPIView(ListAPIView):
    """List all schools with its corresponding Enrollees per Day"""

    serializer_class = serializers.EnrolleesPerDayPerSchoolSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        return user_schools_get(user=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["year_level"] = self.request.GET.get("year_level", None)
        return context


@extend_schema(tags=[Tags.STUDENT_REQUESTS])
class StudentRequestCreateAPIView(InlineSerializerMixin, CreateAPIView):
    """Create Request for the authenticated student"""

    permission_classes = [IsAuthenticated, IsStudentUser]
    serializer_class = serializers.StudentRequestCreateSerializer
    output_serializer_class = serializers.StudentRequestOutputSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = services.student_request_create(
            student=self.request.user.student, data=serializer.validated_data
        )

        _data = data.copy()
        _data["type"] = self.request.data.get("type")

        output_serializer = self.output_serializer_class(data=_data)
        output_serializer.is_valid(raise_exception=True)
        return Response(output_serializer.data)


@extend_schema(tags=[Tags.CHANGE_SCHEDULE_REQUESTS])
class ChangeScheduleRequestListRetrieveUpdateAPIView(
    PermissionRequiredMixin, ListRetrieveUpdateViewSet
):
    summaries = {
        "list": "Change Request List",
        "retrieve": "Change Request Retrieve",
        "update": "Change Request Update",
        "partial_update": "Change Request Update",
    }

    school_field = "student__course__school"

    class Filter(SchoolFilterSet):
        class Meta:
            model = ChangeScheduleRequest
            fields = ["student__course__school", "status"]

    Filter.school_field = school_field

    pagination_class = PageNumberPagination

    permission_classes = [IsAuthenticated, IsAdminUser]
    permission = ["core_students.view_changeschedulerequest"]
    permissions = {
        "list": ["core_students.view_changeschedulerequest"],
        "retrieve": ["core_students.view_changeschedulerequest"],
        "update": ["core_students.change_changeschedulerequest"],
        "partial_update": ["core_students.change_changeschedulerequest"],
    }

    serializer_class = serializers.ChangeRequestRequestListSerializer
    serializer_classes = {
        "list": serializers.ChangeRequestRequestListSerializer,
        "retrieve": serializers.ChangeRequestRequestRetrieveSerializer,
        "update": serializers.ChangeScheduleRequestUpdateSerializer,
        "partial_update": serializers.ChangeScheduleRequestUpdateSerializer,
    }

    filter_backends = [SchoolFilter, DjangoFilterBackend, OrderingFilter]
    filterset_class = Filter

    ordering_fields = ["id"]
    ordering = ["id"]

    def get_queryset(self):
        return ChangeScheduleRequest.objects.all()

    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.serializer_class)

    def perform_update(self, serializer):
        serializer.instance = services.change_schedule_request_update(
            request=self.get_object(),
            user=self.request.user,
            data=serializer.validated_data,
        )


@extend_schema(tags=[Tags.ADD_SUBJECT_REQUESTS])
class AddSubjectRequestListRetrieveUpdateAPIView(
    PermissionRequiredMixin, ListRetrieveUpdateViewSet
):
    summaries = {
        "list": "Add Subject List",
        "retrieve": "Add Subject Retrieve",
        "update": "Add Subject Update",
        "partial_update": "Add Subject Update",
    }

    school_field = "student__course__school"

    class Filter(SchoolFilterSet):
        class Meta:
            model = AddSubjectRequest
            fields = ["student__course__school", "status"]

    Filter.school_field = school_field

    pagination_class = PageNumberPagination

    permission_classes = [IsAuthenticated, IsAdminUser]
    permission = ["core_students.view_addsubjectrequest"]
    permissions = {
        "list": ["core_students.view_addsubjectrequest"],
        "retrieve": ["core_students.view_addsubjectrequest"],
        "update": ["core_students.change_addsubjectrequest"],
        "partial_update": ["core_students.change_addsubjectrequest"],
    }

    serializer_class = serializers.AddSubjectRequestListSerializer
    serializer_classes = {
        "list": serializers.AddSubjectRequestListSerializer,
        "retrieve": serializers.AddSubjectRequestRetrieveSerializer,
        "update": serializers.AddSubjectRequestUpdateSerializer,
        "partial_update": serializers.AddSubjectRequestUpdateSerializer,
    }

    filter_backends = [SchoolFilter, DjangoFilterBackend, OrderingFilter]
    filterset_class = Filter

    ordering_fields = ["id"]
    ordering = ["id"]

    def get_queryset(self):
        return AddSubjectRequest.objects.all()

    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.serializer_class)

    def perform_update(self, serializer):
        serializer.instance = services.add_subject_request_update(
            request=self.get_object(),
            user=self.request.user,
            data=serializer.validated_data,
        )


@extend_schema(tags=[Tags.OPEN_CLASS_REQUESTS])
class OpenClassRequestListRetrieveUpdateAPIView(
    PermissionRequiredMixin, ListRetrieveUpdateViewSet
):
    summaries = {
        "list": "Open Class List",
        "retrieve": "Open Class Retrieve",
        "update": "Open Class Update",
        "partial_update": "Open Class Update",
    }

    school_field = "student__course__school"

    class Filter(SchoolFilterSet):
        class Meta:
            model = OpenClassRequest
            fields = ["student__course__school", "status"]

    Filter.school_field = school_field

    pagination_class = PageNumberPagination

    permission_classes = [IsAuthenticated, IsAdminUser]
    permission = ["core_students.view_openclassrequest"]
    permissions = {
        "list": ["core_students.view_openclassrequest"],
        "retrieve": ["core_students.view_openclassrequest"],
        "update": ["core_students.change_openclassrequest"],
        "partial_update": ["core_students.change_openclassrequest"],
    }

    serializer_class = serializers.OpenClassRequestListSerializer
    serializer_classes = {
        "list": serializers.OpenClassRequestListSerializer,
        "retrieve": serializers.OpenClassRequestRetrieveSerializer,
        "update": serializers.OpenClassRequestUpdateSerializer,
        "partial_update": serializers.OpenClassRequestUpdateSerializer,
    }

    filter_backends = [SchoolFilter, DjangoFilterBackend, OrderingFilter]
    filterset_class = Filter

    ordering_fields = ["id"]
    ordering = ["id"]

    def get_queryset(self):
        return OpenClassRequest.objects.all()

    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.serializer_class)

    def perform_update(self, serializer):
        serializer.instance = services.open_class_request_update(
            request=self.get_object(),
            user=self.request.user,
            data=serializer.validated_data,
        )


@extend_schema(tags=[Tags.WITHDRAWAL_REQUESTS])
class WithdrawalRequestListRetrieveUpdateAPIView(
    PermissionRequiredMixin, ListRetrieveUpdateViewSet
):
    summaries = {
        "list": "Withdrawal Request List",
        "retrieve": "Withdrawal Request Retrieve",
        "update": "Withdrawal Request Update",
        "partial_update": "Withdrawal Request Update",
    }

    school_field = "student__course__school"

    class Filter(SchoolFilterSet):
        class Meta:
            model = WithdrawalRequest
            fields = ["student__course__school", "status"]

    Filter.school_field = school_field

    pagination_class = PageNumberPagination

    permission_classes = [IsAuthenticated, IsAdminUser]
    permission = ["core_students.view_withdrawalrequest"]
    permissions = {
        "list": ["core_students.view_withdrawalrequest"],
        "retrieve": ["core_students.view_withdrawalrequest"],
        "update": ["core_students.change_withdrawalrequest"],
        "partial_update": ["core_students.change_withdrawalrequest"],
    }

    serializer_class = serializers.WithdrawalRequestListSerializer
    serializer_classes = {
        "list": serializers.WithdrawalRequestListSerializer,
        "retrieve": serializers.WithdrawalRequestRetrieveSerializer,
        "update": serializers.WithdrawalRequestUpdateSerializer,
        "partial_update": serializers.WithdrawalRequestUpdateSerializer,
    }

    filter_backends = [SchoolFilter, DjangoFilterBackend, OrderingFilter]
    filterset_class = Filter

    ordering_fields = ["id"]
    ordering = ["id"]

    def get_queryset(self):
        return WithdrawalRequest.objects.all()

    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.serializer_class)

    def perform_update(self, serializer):
        serializer.instance = services.withdrawal_request_update(
            request=self.get_object(),
            user=self.request.user,
            data=serializer.validated_data,
        )


@extend_schema(tags=[Tags.STUDENT_ENROLLMENT])
class StudentEnrollmentSubjectListAPIView(InlineSerializerMixin, ListAPIView):
    """List all subjects that can be enrolled by the student"""

    permission_classes = [IsAuthenticated, IsStudentUser]
    serializer_class = serializers.StudentEnrollmentSubjectListSerializer

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        "subject__course_code": ["icontains"],
        "subject__course_number": ["icontains"],
        "subject__descriptive_code": ["icontains"],
        "subject__descriptive_title": ["icontains"],
    }
    search_fields = [
        "subject__course_code",
        "subject__course_number",
        "subject__descriptive_code",
        "subject__descriptive_title",
    ]
    ordering_fields = ["subject__course_code"]
    ordering = ["subject__course_code"]

    def get_queryset(self):
        passed_curr_subj_ids = self.get_serializer_context().get("passed_curr_subj_ids")
        return selectors.enrollment_subjects_list(
            student=self.request.user.student, passed_curr_subj_ids=passed_curr_subj_ids
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        enrolled_classes = self.request.user.student.enrolled_classes.filter(
            status=EnrolledClass.Statuses.ENROLLED, curriculum_subject__isnull=False
        )

        passed_curr_subj_ids = [
            enrolled_class.curriculum_subject.id
            for enrolled_class in enrolled_classes.filter(
                grades__status=EnrolledClassGrade.Statuses.PASSED
            )
        ]
        context["passed_curr_subj_ids"] = passed_curr_subj_ids
        return context

@extend_schema(tags=[Tags.DASHBOARDS])
class OverallTotalEnrolleesListAPIView(GenericAPIView):
    """Overall Total Enrollees for the Current Semester"""
    
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        return Enrollment.objects.all()

    def get(self, request, *args, **kwargs):
        total_enrollees = selectors.overall_total_enrollees(
            year_level = request.GET.get("year_level", None),
        )
        return Response(
            {"overall_total_enrollees": total_enrollees},
            status = status.HTTP_202_ACCEPTED,
        )
