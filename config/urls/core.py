"""
URL Configuration for university/core service.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django_js_reverse import views as js_reverse_views
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView

from university.framework.views import EnumListApi, HealthCheckApi

urlpatterns = [
    path("admin/", admin.site.urls),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularRedocView.as_view(url_name="schema"), name="docs"),
    path("reverse.js", js_reverse_views.urls_js, name="js_reverse"),
    path("reverse.json", js_reverse_views.urls_json, name="js_reverse-json"),
    path("api/enums/", EnumListApi.as_view(), name="enums-list"),
    path("api/", include("university.core.accounts.urls")),
    path("api/", include("university.core.cms.urls")),
    path("api/", include("university.core.students.urls")),
    path("api/", include("university.core.maintenance.urls")),
    path("api/", include("university.payment.urls")),
    path("healthcheck/", HealthCheckApi.as_view(), name="healthcheck"),
    path("", include("university.payment.service.urls")),
]

if settings.STORAGE_PROVIDER == "system":
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.ENABLE_SILK:
    urlpatterns += [path("silk/", include("silk.urls", namespace="silk"))]
