from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

app_name = "university.core.cms"

router = SimpleRouter()
router.register("classes", views.ClassViewset, basename="classes")
router.register("subjects", views.SubjectViewset, basename="subjects")
router.register("curriculums", views.CurriculumViewset, basename="curriculums")
router.register("courses", views.CourseListRetrieveAPIView, basename="courses")
router.register("buildings", views.BuildingListRetrieveAPIView, basename="buildings")
router.register("fees", views.FeeListRetrieveAPIView, basename="fees")
router.register(
    "fee-specifications",
    views.FeeSpecificationListRetrieveAPIView,
    basename="fee-specifications",
)
router.register(
    "curriculum-periods", views.CurriculumPeriodViewset, basename="curriculum-periods"
)
router.register("rooms", views.RoomViewSet, basename="rooms")
router.register(
    "room-classifications",
    views.RoomClassificationListRetrieveAPIView,
    basename="room-classifications",
)
router.register("discounts", views.DiscountListRetrieveAPIView, basename="discounts")

urlpatterns = [
    path(
        "class-schedules/",
        views.PersonnelClassScheduleListAPIView.as_view(),
        name="class-schedules",
    ),
    path(
        "open-classes-per-school/",
        views.OpenClassPerSchoolListAPIView.as_view(),
        name="open-classes-per-school",
    ),
    path(
        "classes-enrollees-per-course/",
        views.OpenClassEnrolleePerCourseListAPIView.as_view(),
        name="classes-enrollees-per-course",
    ),
    path(
        "class-grade-states-per-school/",
        views.ClassGradeStatePerSchoolListAPIView.as_view(),
        name="class-grade-states-per-school",
    ),
    
]
announcements_urlpatterns = [
    path(
        "announcements/",
        views.AnnouncementsListAPIView.as_view(),
        name="announcements-list",
    ),
    path(
        "announcements/details/",
        views.AnnouncementsListCreateAPIView.as_view(),
        name="announcements-details",
    ),
    path(
        "announcements/details/<pk>",
        views.AnnouncementsUpdateDestroyAPIView.as_view(),
        name="announcements-details",
    ),
]

urlpatterns += router.urls
urlpatterns += announcements_urlpatterns
