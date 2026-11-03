import csv

import structlog
from django.contrib.auth import get_user_model
from django.db import transaction as db_transaction
from django.http import HttpResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import serializers as drf_serializers
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import (
    GenericAPIView,
    ListAPIView,
    ListCreateAPIView,
    RetrieveAPIView,
    RetrieveUpdateDestroyAPIView,
    UpdateAPIView,
)
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.settings.openapi import Tags
from university.core.accounts.filters import SchoolFilter, SchoolFilterSet
from university.core.accounts.models import AcademicYear
from university.core.accounts.selectors import current_semester_get, user_schools_get
from university.framework.events import event_publisher
from university.framework.pagination import PageNumberPagination
from university.framework.permissions import IsAdminUser, IsStudentUser, IsSuperUser
from university.framework.views import (
    ApiSerializerClassMixin,
    ObjectPermissionRequiredMixin,
    PermissionRequiredMixin,
)

from . import events, models, selectors, serializers, services
from .clients import BukasClient

User = get_user_model()

log = structlog.get_logger(__name__)
bukas_client = BukasClient()


class StatementOfAccountListAPIView(ListAPIView):
    """List all SOA"""

    queryset = models.StatementOfAccount.objects.all()
    serializer_class = serializers.StatementOfAccountSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]


@extend_schema(tags=[Tags.STATEMENT_OF_ACCOUNTS])
class StudentSOALatestAPIView(RetrieveAPIView):
    """Get latest SOA of authenticated student"""

    serializer_class = serializers.StatementOfAccountSerializer
    permission_classes = [IsAuthenticated, IsStudentUser]

    def get_queryset(self):
        return models.StatementOfAccount.objects.filter(user=self.request.user)

    def get_object(self):
        obj = selectors.soa_get_latest(user=self.request.user)
        # May raise a permission denied
        self.check_object_permissions(self.request, obj)
        return obj


@extend_schema(deprecated=True)
class StatementOfAccountLatestAPIView(StudentSOALatestAPIView):
    pass


@extend_schema(tags=[Tags.STATEMENT_OF_ACCOUNTS])
class StudentSOAListAPIView(ListAPIView):
    """List SOA of authenticated student"""

    serializer_class = serializers.StatementOfAccountSerializer
    permission_classes = [IsAuthenticated, IsStudentUser]

    def get_queryset(self):
        return models.StatementOfAccount.objects.filter(user=self.request.user)


class PaymentCreateAPIVew(APIView):
    """Payment Create"""

    serializer_class = serializers.PaymentCreateSerializer
    permission_classes = [IsAuthenticated, IsStudentUser]

    serializer_classes_by_payment_method = {
        models.PaymentMethods.DRAGONPAY.value: serializers.DragonpayPaymentCreateSerializer,
        models.PaymentMethods.BUKAS.value: serializers.PaymentCreateSerializer,
        models.PaymentMethods.OTC.value: serializers.OverTheCounterCreateSerializer,
        models.PaymentMethods.CASHIER.value: serializers.PaymentCreateSerializer,
    }
    output_serializer_classes_by_payment_method = {
        models.PaymentMethods.DRAGONPAY.value: serializers.DragonpayPaymentOutputSerializer,
        models.PaymentMethods.BUKAS.value: serializers.BukasPaymentOutputSerializer,
        models.PaymentMethods.OTC.value: serializers.OverTheCounterOutputSerializer,
        models.PaymentMethods.CASHIER.value: serializers.CashierOutputSerializer,
    }

    def get_serializer_class(self):
        payment_method = self.request.data.get("payment_method")
        return (
            self.serializer_classes_by_payment_method.get(payment_method)
            or self.serializer_class
        )

    def get_output_serializer_class(self):
        payment_method = self.request.data.get("payment_method")
        return (
            self.output_serializer_classes_by_payment_method.get(payment_method)
            or self.serializer_class
        )

    def post(self, request):
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = services.payment_create(
            user=request.user, data=serializer.validated_data
        )

        if not data:
            raise ValidationError({"error": "Failed to create payment transaction"})

        _data = data.copy()
        _data["payment_method"] = request.data.get("payment_method")

        output_serializer_class = self.get_output_serializer_class()
        output_serializer = output_serializer_class(data=_data)
        output_serializer.is_valid(raise_exception=True)
        return Response(output_serializer.data)


class DragonpayTransactionListAPIView(PermissionRequiredMixin, ListAPIView):
    """Dragonpay Transaction List"""

    school_field = "soa__enrollment__student__course__school"

    class Filter(SchoolFilterSet):
        class Meta:
            model = models.DragonpayTransaction
            fields = ["school", "channel", "status"]

    Filter.school_field = school_field

    queryset = models.DragonpayTransaction.objects.order_by("-id")
    pagination_class = PageNumberPagination
    serializer_class = serializers.DragonpayTransactionListApiSerializer

    filter_backends = [SchoolFilter, DjangoFilterBackend, SearchFilter]
    filterset_class = Filter
    search_fields = [
        "payment_id",
        "soa__user__student__first_name",
        "soa__user__student__last_name",
        "soa__user__student__id_number",
    ]

    permission_classes = [IsAuthenticated, IsAdminUser]
    permission = ["payment.view_dragonpaytransaction"]


@extend_schema(tags=[Tags.DRAGONPAY_CHANNELS])
class DragonpayChannelListCreateAPIView(ListCreateAPIView):
    class OutputSerializer(drf_serializers.ModelSerializer):
        class Meta:
            model = models.DragonpayChannel
            fields = (
                "id",
                "proc_id",
                "description",
                "addon_percentage",
                "addon_fixed",
                "is_active",
            )

    serializer_class = OutputSerializer
    pagination_class = PageNumberPagination

    def get_permissions(self):
        method = self.request.method.lower()

        if method == "get":
            perms = [IsAuthenticated, IsAdminUser | IsStudentUser]
        else:
            perms = [IsAuthenticated, IsAdminUser]

        return [permission() for permission in perms]

    def get_queryset(self):
        qs = models.DragonpayChannel.active_objects.all()

        if self.request.user.type == User.Types.STUDENT:
            return qs.filter(is_active=True).order_by("description")

        return qs.order_by("description")

    def paginate_queryset(self, queryset):
        if self.request.user.type == User.Types.STUDENT:
            return None
        return super().paginate_queryset(queryset)


@extend_schema(tags=[Tags.DRAGONPAY_CHANNELS])
class DragonpayChannelUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    class InputSerializer(drf_serializers.ModelSerializer):
        class Meta:
            model = models.DragonpayChannel
            fields = (
                "proc_id",
                "description",
                "addon_percentage",
                "addon_fixed",
                "is_active",
            )

    queryset = models.DragonpayChannel.active_objects.all()
    serializer_class = InputSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    http_method_names = RetrieveUpdateDestroyAPIView.http_method_names.copy()
    http_method_names.remove("get")

    def perform_destroy(self, instance):
        instance.soft_delete()


@extend_schema(tags=[Tags.DRAGONPAY_CHANNELS])
class DragonpayChannelListStudentCreateAPIView(ListAPIView):
    class OutputSerializer(drf_serializers.ModelSerializer):
        class Meta:
            model = models.DragonpayChannel
            fields = (
                "id",
                "proc_id",
                "description",
                "addon_percentage",
                "addon_fixed",
                "is_active",
            )

    serializer_class = OutputSerializer

    def get_permissions(self):
        method = self.request.method.lower()

        if method == "get":
            perms = [IsAuthenticated, IsAdminUser | IsStudentUser]
        else:
            perms = [IsAuthenticated, IsAdminUser]

        return [permission() for permission in perms]

    def get_queryset(self):
        qs = models.DragonpayChannel.active_objects.all()

        if self.request.user.type == User.Types.STUDENT:
            return qs.filter(is_active=True).order_by("description")

        return qs.order_by("description")


class BukasTransactionListAPIView(PermissionRequiredMixin, ListAPIView):
    """Bukas Transaction List"""

    school_field = "soa__enrollment__student__course__school"

    class Filter(SchoolFilterSet):
        class Meta:
            model = models.BukasTransaction
            fields = ["school", "status"]

    Filter.school_field = school_field

    queryset = models.BukasTransaction.objects.all()
    pagination_class = PageNumberPagination
    serializer_class = serializers.BukasTransactionListApiSerializer

    filter_backends = [SchoolFilter, DjangoFilterBackend, SearchFilter]
    filterset_class = Filter
    search_fields = [
        "payment_id",
        "soa__user__student__first_name",
        "soa__user__student__last_name",
        "soa__user__student__id_number",
    ]

    permission_classes = [IsAuthenticated, IsAdminUser]
    permission = ["payment.view_bukastransaction"]


class OtcTransactionListApi(PermissionRequiredMixin, ListAPIView):
    """OTC Transaction List"""

    school_field = "soa__enrollment__student__course__school"

    class Filter(SchoolFilterSet):
        class Meta:
            model = models.OverTheCounterTransaction
            fields = ["school", "status"]

    Filter.school_field = school_field

    queryset = models.OverTheCounterTransaction.objects.order_by("-id")
    pagination_class = PageNumberPagination
    serializer_class = serializers.OtcTransactionListApiSerializer

    filter_backends = [SchoolFilter, DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = Filter
    search_fields = [
        "payment_id",
        "soa__user__student__first_name",
        "soa__user__student__last_name",
        "soa__user__student__id_number",
    ]
    ordering_fields = ["amount", "settled_at", "created_at"]

    permission_classes = [IsAuthenticated, IsAdminUser]
    permission = ["payment.view_cashiertransaction"]


class CashierTransactionListApi(PermissionRequiredMixin, ListAPIView):
    """Cashier Transaction List"""

    school_field = "soa__enrollment__student__course__school"

    class Filter(SchoolFilterSet):
        class Meta:
            model = models.CashierTransaction
            fields = ["school", "status"]

    Filter.school_field = school_field

    queryset = models.CashierTransaction.objects.order_by("-id")
    pagination_class = PageNumberPagination
    serializer_class = serializers.CashierTransactionListApiSerializer

    filter_backends = [SchoolFilter, DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = Filter
    search_fields = [
        "payment_id",
        "soa__user__student__first_name",
        "soa__user__student__last_name",
        "soa__user__student__id_number",
    ]
    ordering_fields = ["amount", "processed_at", "processed_by"]

    permission_classes = [IsAuthenticated, IsAdminUser]
    permission = ["payment.view_cashiertransaction"]


class CashierTransactionUpdateApi(ObjectPermissionRequiredMixin, UpdateAPIView):
    """Cashier Transaction Update"""

    queryset = models.CashierTransaction.objects.all()
    serializer_class = serializers.CashierTransactionUpdateApiSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    permission = ["payment.change_cashiertransaction"]
    lookup_field = "payment_id"


class CashierTransactionPaidApi(PermissionRequiredMixin, GenericAPIView):
    """Cashier Transaction Tag as Paid"""

    queryset = models.CashierTransaction.objects.all()
    serializer_class = serializers.CashierTransactionPaidApiSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    permission = ["payment.change_cashiertransaction"]

    def post(self, request, payment_id):
        with db_transaction.atomic():
            transaction = selectors.cashier_transaction_get(
                payment_id=payment_id, raise_exception=True, lock=True
            )
            self.check_permissions(request)

            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)

            services.cashier_transaction_tag_as_paid(
                transaction=transaction,
                cashier=request.user,
                **serializer.validated_data,
            )

        event_publisher.generic(events.PAYMENT_SUCCESS, object=transaction)
        return Response(status=status.HTTP_202_ACCEPTED)


class CashierTransactionVoidApi(PermissionRequiredMixin, GenericAPIView):
    """Cashier Transaction Void"""

    queryset = models.CashierTransaction.objects.all()
    serializer_class = serializers.CashierTransactionVoidApiSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    permission = ["payment.change_cashiertransaction"]

    @db_transaction.atomic
    def post(self, request, payment_id):
        transaction = selectors.cashier_transaction_get(
            payment_id=payment_id, raise_exception=True, lock=True
        )
        self.check_permissions(request)

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        services.cashier_transaction_void(
            transaction=transaction, cashier=request.user, **serializer.validated_data
        )
        return Response(status=status.HTTP_202_ACCEPTED)


class PaymentSettlementApi(ApiSerializerClassMixin, ListCreateAPIView):
    queryset = models.PaymentSettlement.objects.order_by("-id")
    parser_classes = [MultiPartParser]

    serializer_class = serializers.PaymentSettlementListApiSerializer
    serializer_classes = {
        "get": serializers.PaymentSettlementListApiSerializer,
        "post": serializers.PaymentSettlementCreateApiSerializer,
    }

    permission_classes = [IsAuthenticated, IsAdminUser]

    def perform_create(self, serializer):
        payment_method = serializer.validated_data.get("payment_method")
        settlement = services.payment_settlement_create(
            file=serializer.validated_data.get("file"),
            payment_method=payment_method,
            jv_number=serializer.validated_data.get("jv_number"),
        )
        serializer.instance = settlement

        event_map = {
            models.PaymentMethods.DRAGONPAY: events.DRAGONPAY_SETTLEMENT_CREATED,
            models.PaymentMethods.BUKAS: events.BUKAS_SETTLEMENT_CREATED,
            models.PaymentMethods.OTC: events.OTC_SETTLEMENT_CREATED,
            models.PaymentMethods.CASHIER: events.CASHIER_SETTLEMENT_CREATED,
        }
        event_publisher.create(
            name=event_map.get(payment_method),
            actor=self.request.user,
            target=settlement,
        )


class JournalVoucherApi(ApiSerializerClassMixin, ListCreateAPIView):
    queryset = models.JournalVoucher.objects.order_by("-id")
    parser_classes = [MultiPartParser]

    serializer_class = serializers.JournalVoucherListApiSerializer
    serializer_classes = {
        "get": serializers.JournalVoucherListApiSerializer,
        "post": serializers.JournalVoucherCreateApiSerializer,
    }

    permission_classes = [IsAuthenticated, IsAdminUser]

    def perform_create(self, serializer):
        jv = services.journal_voucher_create(file=serializer.validated_data.get("file"))
        serializer.instance = jv
        event_publisher.create(
            name=events.JOURNAL_VOUCHER_CREATED, actor=self.request.user, target=jv
        )


@extend_schema(exclude=True)
class DragonpaySettlementTestFileApi(APIView):
    """Generate dragonpay settlement test file

    For Django Admin use only.
    """

    permission_classes = [IsAuthenticated, IsSuperUser]

    def get(self, request):
        now = timezone.now()

        response = HttpResponse(content_type="text/csv")
        filename = f"Dragonpay Settlement {now.strftime('%Y-%m-%d %H-%M-%S')}.csv"
        content_disposition = f"attachment;filename={filename}"
        response["Content-Disposition"] = content_disposition

        fieldnames = [
            "Create Date",
            "Settle Date",
            "Refno",
            "Merchant Txn Id",
            "Ccy",
            "Amount",
            "Fee",
            "Settlement",
            "Proc",
            "Description",
        ]
        writer = csv.DictWriter(response, fieldnames=fieldnames)
        writer.writeheader()

        test_csv = selectors.dragonpay_settlement_test_csv_generate()

        for data in test_csv:
            writer.writerow(data)

        return response


@extend_schema(exclude=True)
class CashierSettlementTestFileApi(APIView):
    """Generate cashier settlement test file

    For Django Admin use only.
    """

    permission_classes = [IsAuthenticated, IsSuperUser]

    def get(self, request):
        now = timezone.now()

        response = HttpResponse(content_type="text/csv")
        filename = f"Cashier Settlement {now.strftime('%Y-%m-%d %H-%M-%S')}.csv"
        content_disposition = f"attachment;filename={filename}"
        response["Content-Disposition"] = content_disposition

        fieldnames = [
            "IDNO",
            "LASTNAME",
            "FIRSTNAME",
            "MID_NAME",
            "SECTION",
            "LEVEL",
            "CUSTOMER",
            "ACCNT_NO",
            "EXPL",
            "REFERENCE",
            "DATE",
            "CHK_AMT",
            "CASH",
            "AMOUNT",
            "BATCH",
            "TRANSF",
            "DIV",
            "CUST_NO",
            "CO",
            "CC",
            "GLNO",
            "SSS",
            "BIRTHDATE",
            "FATHER",
            "MOTHER",
            "NEW",
        ]
        writer = csv.DictWriter(response, fieldnames=fieldnames)
        writer.writeheader()

        test_csv = selectors.cashier_settlement_test_csv_generate()

        for data in test_csv:
            writer.writerow(data)

        return response


@extend_schema(exclude=True)
class JournalVoucherTestFileApi(APIView):
    """Generate journal voucher test file

    For Django Admin use only.
    """

    permission_classes = [IsAuthenticated, IsSuperUser]

    def get(self, request):
        now = timezone.now()

        response = HttpResponse(content_type="text/csv")
        filename = f"Journal Voucher {now.strftime('%Y-%m-%d %H-%M-%S')}.csv"
        content_disposition = f"attachment;filename={filename}"
        response["Content-Disposition"] = content_disposition

        writer = csv.writer(response)
        test_csv = selectors.journal_voucher_test_csv_generate()

        for data in test_csv:
            writer.writerow(data)

        return response


@extend_schema(tags=[Tags.DASHBOARDS])
class PaymentCountPerSchoolListAPIView(ListAPIView):
    """List all schools with its corresponding tally of payment per method"""

    serializer_class = serializers.PaymentCountPerSchoolSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        return user_schools_get(user=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["year_level"] = self.request.GET.get("year_level", None)
        return context


@extend_schema(tags=[Tags.DASHBOARDS])
class TotalRevenueListAPIView(GenericAPIView):
    """Return total revenue across all schools"""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        return user_schools_get(user=self.request.user)

    def get(self, request, *args, **kwargs):
        schools = user_schools_get(user=self.request.user)
        semester = current_semester_get()
        total_revenue = selectors.total_revenue_get(
            schools=schools,
            semester=semester,
            year_level=request.GET.get("year_level", None),
        )
        return Response(
            {"total_revenue": total_revenue},
            status=status.HTTP_202_ACCEPTED,
        )


@extend_schema(tags=[Tags.DASHBOARDS])
class OverTheCounterStatusCountPerSchoolListAPIView(ListAPIView):
    """List all schools with its corresponding Over The Counter Payment Status"""

    serializer_class = serializers.OverTheCounterStatusPerSchoolSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        return user_schools_get(user=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["year_level"] = self.request.GET.get("year_level", None)
        return context


@extend_schema(tags=[Tags.DASHBOARDS])
class PaymentMethodCountListAPIView(ListAPIView):
    """List of Payment Method Used Based from the Current Enrollment"""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        return user_schools_get(user=self.request.user)

    def get(self, request, *args, **kwargs):
        semester = current_semester_get()
        payment_methods = selectors.payment_method_percentage_get(
            semester=semester,
            year_level=request.GET.get("year_level", None),
        )

        return Response(
            {"payment_methods": payment_methods},
            status=status.HTTP_202_ACCEPTED,
        )


@extend_schema(tags=[Tags.DASHBOARDS])
class PaymentStatusPerSchoolCountListAPIView(ListAPIView):
    """List of Schools with corresponding Remaining Balance and Fully Paid Payment Status"""

    serializer_class = serializers.PaymentStatusPerSchoolSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        return user_schools_get(user=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["year_level"] = self.request.GET.get("year_level", None)
        return context


@extend_schema(tags=[Tags.DASHBOARDS])
class RevenuePerMethodPerSchoolYearListAPIView(ListAPIView):
    """List of Revenue per methods per Academic Year"""

    serializer_class = serializers.RevenuePerMethodPerSchoolYearSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["year_start"]
    ordering_fields = ["year_start"]
    ordering = ["year_start"]

    def get_queryset(self):
        return AcademicYear.objects.all()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["year_level"] = self.request.GET.get("year_level", None)
        return context


@extend_schema(tags=[Tags.OTC])
class StudentOTCTransactionUpdateApi(UpdateAPIView):
    """Student OTC Transaction Update"""

    queryset = models.OverTheCounterTransaction.objects.all()
    serializer_class = serializers.StudentOTCTransactionUpdateApiSerializer
    permission_classes = [IsAuthenticated, IsStudentUser]
    lookup_field = "payment_id"


@extend_schema(tags=[Tags.CASHIER])
class StudentCashierTransactionUpdateApi(UpdateAPIView):
    """Student Cashier Transaction Update"""

    queryset = models.CashierTransaction.objects.all()
    serializer_class = serializers.StudentCashierTransactionUpdateApiSerializer
    permission_classes = [IsAuthenticated, IsStudentUser]
    lookup_field = "payment_id"
