from django.urls import include, path
from rest_framework.routers import SimpleRouter

from . import views

app_name = "university.core.students"

router = SimpleRouter()
router.register("students", views.StudentListRetrieveAPIView, basename="students")

router.register(
    "change-schedule-requests",
    views.ChangeScheduleRequestListRetrieveUpdateAPIView,
    basename="change-schedule-requests",
)
router.register(
    "add-subject-requests",
    views.AddSubjectRequestListRetrieveUpdateAPIView,
    basename="add-subject-requests",
)
router.register(
    "open-class-requests",
    views.OpenClassRequestListRetrieveUpdateAPIView,
    basename="open-class-requests",
)

router.register(
    "withdrawal-requests",
    views.WithdrawalRequestListRetrieveUpdateAPIView,
    basename="withdrawal-requests",
)

admin_urls = [
    path(
        "students/<pk>/grades/",
        views.StudentClassGradeListAPIView.as_view(),
        name="student-grades",
    ),
    path(
        "classes/<pk>/grades/",
        views.EnrolledClassGradeListAPIView.as_view(),
        name="class-grades",
    ),
    path(
        "grade-sheets/",
        views.GradeSheetApi.as_view(),
        name="grade-sheets",
    ),
    path(
        "grade-sheets/<file_id>/",
        views.GradeSheetDetailApi.as_view(),
        name="grade-sheets-detail",
    ),
    path(
        "grade-sheets/<file_id>/draft/",
        views.GradeSheetDraftApi.as_view(),
        name="grade-sheets-draft",
    ),
    path(
        "grade-sheets/<file_id>/submit/",
        views.GradeSheetSubmitApi.as_view(),
        name="grade-sheets-submit",
    ),
    path(
        "enrollments/remark-update/",
        views.EnrollmentRemarkUpdateAPIView.as_view(),
        name="enrollment-remark-update",
    ),
    path(
        "enrollments/status-update/",
        views.EnrollmentStatusUpdateAPIView.as_view(),
        name="enrollment-status-update",
    ),
    path(
        "enrollments/for-evaluation/",
        views.PreEnrollmentListAPIView.as_view(),
        name="enrollments-for-evaluation",
    ),
    path(
        "enrollment-gwa/",
        views.EnrollmentGWAUploadAPI.as_view(),
        name="enrollment-gwa-upload",
    ),
]


admin_dashboard_urls = [
    path(
        "enrollees-per-school/",
        views.EnrolleePerSchoolListAPIView.as_view(),
        name="enrollees-per-school",
    ),
    path(
        "failed-students-per-school/",
        views.FailedStudentPerSchoolListAPIView.as_view(),
        name="failed-students-per-school",
    ),
    path(
        "interviewed-failed-students-per-school/",
        views.InterviewedFailedStudentPerSchoolListAPIView.as_view(),
        name="interviewed-failed-students-per-school",
    ),
    path(
        "enrollees-scholars-per-school/",
        views.EnrolleeScholarPerSchoolListAPIView.as_view(),
        name="enrollees-scholars-per-school",
    ),
    path(
        "enrollees-per-day-per-school/",
        views.EnrolleesPerDayPerSchoolListAPIView.as_view(),
        name="enrollees-per-day-per-school",
    ),
    path(
        "overall-total-enrollees",
        views.OverallTotalEnrolleesListAPIView.as_view(),
        name="overall-total-enrollees",
    )
]

student_urlpatterns = [
    path(
        "",
        views.StudentProfileApi.as_view(),
        name="profile",
    ),
    path(
        "enrollment/",
        views.StudentEnrollmentCreateAPIView.as_view(),
        name="enrollment-create",
    ),
    path(
        "enrollment-subjects/",
        views.StudentEnrollmentSubjectListAPIView.as_view(),
        name="enrollment-subjects-list",
    ),
    path(
        "enrollments/",
        views.StudentEnrollmentListAPIView.as_view(),
        name="enrollments-list",
    ),
    path(
        "enrollments/latest/",
        views.StudentEnrollmentOngoingAPIView.as_view(),
        name="enrollments-latest",
    ),
    path(
        "enrollments/active/",
        views.StudentEnrollmentActiveAPIView.as_view(),
        name="enrollments-active",
    ),
    path(
        "classes/",
        views.StudentClassListAPIView.as_view(),
        name="classes-list",
    ),
    path(
        "curriculum/",
        views.StudentCurriculumRetrieveAPIView.as_view(),
        name="curriculum-detail",
    ),
    path(
        "grades/",
        views.StudentEnrollmentGradeListAPIView.as_view(),
        name="grades-list",
    ),
    path(
        "request/",
        views.StudentRequestCreateAPIView.as_view(),
        name="student-request-create",
    ),
]

urlpatterns = (
    [
        path("student/", include((student_urlpatterns, "student"))),
    ]
    + admin_urls
    + admin_dashboard_urls
)

urlpatterns += router.urls
