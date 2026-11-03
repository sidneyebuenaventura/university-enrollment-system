from django.urls import path

from . import views

app_name = "university.payment.service"

urlpatterns = [
    path(
        "transactions/<str:id>/",
        views.PaymentTransactionView.as_view(),
        name="transaction-view",
    ),
    path(
        "bukas-redirect-url/",
        views.BukasRedirectView.as_view(),
        name="bukas-redirect-url",
    ),
    path(
        "dragonpay/",
        views.DragonpayReturnView.as_view(),
        name="dragonpay-return",
    ),
]

api_urlpatterns = [
    path(
        "api/dragonpay/postback/",
        views.DragonpayPostbackAPIView.as_view(),
        name="dragonpay-postback",
    ),
    path(
        "api/bukas/webhook/",
        views.BukasWebhookAPIView.as_view(),
        name="bukas-webhook",
    ),
]

urlpatterns += api_urlpatterns
