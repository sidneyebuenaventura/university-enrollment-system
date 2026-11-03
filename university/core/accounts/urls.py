from django.urls import include, path
from rest_framework.routers import SimpleRouter

from . import views

app_name = "university.core.accounts"

router = SimpleRouter()
router.register("staffs", views.StaffViewSet, basename="staffs")
router.register("roles", views.RoleViewSet, basename="roles")
router.register("schools", views.SchoolViewSet, basename="schools")
router.register("departments", views.DepartmentViewSet, basename="departments")
router.register("faculty", views.FacultyListRetrieveViewSet, basename="faculty")
router.register("semesters", views.SemesterListRetrieveViewset, basename="semesters")
router.register(
    "academic-years", views.AcademicYearListRetrieveViewset, basename="academic-years"
)

urlpatterns = [
    path(
        "profile/",
        views.PersonnelProfileApi.as_view(),
        name="profile",
    ),
    path(
        "permissions/",
        views.PermissionListAPIView.as_view(),
        name="permissions-list",
    ),
    path(
        "modules/",
        views.ModuleListAPIView.as_view(),
        name="modules-list",
    ),
    path(
        "academic-years/current/",
        views.AcademicYearCurrentAPIView.as_view(),
        name="academic-years-current",
    ),
    path(
        "semesters/upcoming/",
        views.SemesterUpcomingAPIView.as_view(),
        name="semesters-upcoming",
    ),
    path(
        "semesters/previous/",
        views.SemesterPreviousAPIView.as_view(),
        name="semesters-previous",
    ),
]

auth_urlpatterns = [
    path(
        "auth/login-web/",
        views.WebLoginView.as_view(),
        name="login-web",
    ),
    path(
        "auth/login-mobile/",
        views.MobileLoginView.as_view(),
        name="login-mobile",
    ),
    path("auth/logout/", views.LogoutView.as_view(), name="logout"),
    path("auth/user/", views.UserDetailsView.as_view(), name="user-detail"),
    path(
        "auth/password/set/",
        views.PasswordSetView.as_view(),
        name="password-set",
    ),
    path(
        "auth/password/change/",
        views.PasswordChangeView.as_view(),
        name="password-change",
    ),
    path(
        "auth/password/change/waive/",
        views.PasswordChangeWaiveView.as_view(),
        name="password-change-waive",
    ),
    path(
        "auth/password/reset/",
        views.PasswordResetView.as_view(),
        name="password-reset",
    ),
    path(
        "auth/password/reset/confirm/",
        views.PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
]

urlpatterns += router.urls
urlpatterns += auth_urlpatterns
