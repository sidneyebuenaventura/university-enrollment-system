from django.urls import path

from . import views

app_name = "university.payment"

urlpatterns = [
    path(
        "statement-of-accounts/",
        views.StatementOfAccountListAPIView.as_view(),
        name="statement-of-accounts-list",
    ),
    path(
        "student/statement-of-accounts/",
        views.StudentSOAListAPIView.as_view(),
        name="student-statement-of-accounts-list",
    ),
    path(
        "student/statement-of-accounts/latest/",
        views.StudentSOALatestAPIView.as_view(),
        name="student-statement-of-accounts-latest",
    ),
    path(
        "statement-of-accounts/latest/",
        views.StatementOfAccountLatestAPIView.as_view(),
        name="statement-of-accounts-latest",
    ),
    path(
        "payments/",
        views.PaymentCreateAPIVew.as_view(),
        name="payments-create",
    ),
    path(
        "settlements/",
        views.PaymentSettlementApi.as_view(),
        name="payment-settlements-list",
    ),
    path(
        "journal-vouchers/",
        views.JournalVoucherApi.as_view(),
        name="journal-vouchers-list",
    ),
    path(
        "journal-vouchers/test-file/",
        views.JournalVoucherTestFileApi.as_view(),
        name="journal-vouchers-test-file-generate",
    ),
    path(
        "payment-count-per-school/",
        views.PaymentCountPerSchoolListAPIView.as_view(),
        name="payment-count-per-school",
    ),
    path(
        "total-revenue/",
        views.TotalRevenueListAPIView.as_view(),
        name="total-revenue",
    ),
    path(
        "over-the-counter-status-count-per-school/",
        views.OverTheCounterStatusCountPerSchoolListAPIView.as_view(),
        name="over-the-counter-status-count-per-school",
    ),
    path(
        "payment-method-count/",
        views.PaymentMethodCountListAPIView.as_view(),
        name="payment-method-count",
    ),
    path(
        "payment-status-count-per-school/",
        views.PaymentStatusPerSchoolCountListAPIView.as_view(),
        name="payment-status-count-per-school",
    ),
    path(
        "revenue-per-method-per-year/",
        views.RevenuePerMethodPerSchoolYearListAPIView.as_view(),
        name="revenue-per-method-per-year",
    ),
]

dragonpay_urlpatterns = [
    path(
        "dragonpay/transactions/",
        views.DragonpayTransactionListAPIView.as_view(),
        name="dragonpay-transactions-list",
    ),
    path(
        "dragonpay/channels/student-view/",
        views.DragonpayChannelListStudentCreateAPIView.as_view(),
        name="dragonpay-channels-student-view",
    ),
    path(
        "dragonpay/channels/",
        views.DragonpayChannelListCreateAPIView.as_view(),
        name="dragonpay-channels-list",
    ),
    path(
        "dragonpay/channels/<pk>/",
        views.DragonpayChannelUpdateDestroyAPIView.as_view(),
        name="dragonpay-channels-detail",
    ),
    path(
        "dragonpay/settlements/test-file/",
        views.DragonpaySettlementTestFileApi.as_view(),
        name="dragonpay-settlements-test-file-generate",
    ),
]

bukas_urlpatterns = [
    path(
        "bukas/transactions/",
        views.BukasTransactionListAPIView.as_view(),
        name="bukas-transactions-list",
    ),
]

otc_urlpatterns = [
    path(
        "otc/transactions/",
        views.OtcTransactionListApi.as_view(),
        name="otc-transactions-list",
    ),
    path(
        "student/otc/transactions/<payment_id>/",
        views.StudentOTCTransactionUpdateApi.as_view(),
        name="student-otc-transactions-detail",
    ),
]

cashier_urlpatterns = [
    path(
        "cashier/transactions/",
        views.CashierTransactionListApi.as_view(),
        name="cashier-transactions-list",
    ),
    path(
        "cashier/transactions/<payment_id>/",
        views.CashierTransactionUpdateApi.as_view(),
        name="cashier-transactions-detail",
    ),
    path(
        "student/cashier/transactions/<payment_id>/",
        views.StudentCashierTransactionUpdateApi.as_view(),
        name="student-cashier-transactions-detail",
    ),
    path(
        "cashier/transactions/<payment_id>/paid/",
        views.CashierTransactionPaidApi.as_view(),
        name="cashier-transactions-paid",
    ),
    path(
        "cashier/transactions/<payment_id>/void/",
        views.CashierTransactionVoidApi.as_view(),
        name="cashier-transactions-void",
    ),
    path(
        "cashier/settlements/test-file/",
        views.CashierSettlementTestFileApi.as_view(),
        name="cashier-settlements-test-file-generate",
    ),
]

urlpatterns += dragonpay_urlpatterns
urlpatterns += bukas_urlpatterns
urlpatterns += otc_urlpatterns
urlpatterns += cashier_urlpatterns
