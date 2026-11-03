"""
URL Configuration for university/payment service.
"""

from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView

urlpatterns = [
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularRedocView.as_view(url_name="schema"), name="docs"),
    path("api/", include("university.payment.urls")),
    path("", include("university.payment.service.urls")),
]
