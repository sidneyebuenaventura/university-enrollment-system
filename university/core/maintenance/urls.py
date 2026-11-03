from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

app_name = "university.core.maintenance"

router = SimpleRouter()
router.register(
    "enrollment-schedules",
    views.EnrollmentScheduleViewSet,
    basename="enrollment-schedules",
)

urlpatterns = [
    path(
        "module-configurations/",
        views.ModuleConfigurationListAPIView.as_view(),
        name="module-configurations-list",
    ),
]

urlpatterns += router.urls
