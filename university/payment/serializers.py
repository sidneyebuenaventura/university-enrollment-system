from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_polymorphic.serializers import PolymorphicSerializer

from university.core.accounts.models import AcademicYear, School
from university.core.accounts.selectors import current_semester_get
from university.core.students.models import Student
from university.framework.serializers import ChoiceField, inline_serializer_class
from django.db.models import Sum
from university.payment import selectors

from . import models

User = get_user_model()


class PaymentCreateSerializer(serializers.Serializer):
    payment_method = ChoiceField(choices_cls=models.PaymentMethods)


class DragonpayPaymentCreateSerializer(PaymentCreateSerializer):
    amount = serializers.DecimalField(max_digits=9, decimal_places=2)
    channel = serializers.PrimaryKeyRelatedField(
        queryset=models.DragonpayChannel.objects.filter(is_active=True), write_only=True
    )


class DragonpayPaymentOutputSerializer(PaymentCreateSerializer):
    redirect_url = serializers.URLField()


class BukasPaymentOutputSerializer(PaymentCreateSerializer):
    redirect_url = serializers.URLField()


class OverTheCounterCreateSerializer(PaymentCreateSerializer):
    bank = serializers.ChoiceField(choices=models.OverTheCounterTransaction.Banks)


class OverTheCounterOutputSerializer(PaymentCreateSerializer):
    reference_number = serializers.CharField(max_length=255)
    bank = serializers.CharField(max_length=255)


class CashierOutputSerializer(PaymentCreateSerializer):
    reference_number = serializers.CharField(max_length=255)


class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PaymentTransaction
        fields = ("type", "soa", "error_message")


class DragonpayChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.DragonpayChannel
        fields = ("id", "description", "addon_percentage", "addon_fixed")


class DragonpayTransactionSerializer(serializers.ModelSerializer):
    channel = DragonpayChannelSerializer()
    total_amount = serializers.DecimalField(max_digits=9, decimal_places=2)
    total_amount_paid = serializers.DecimalField(max_digits=9, decimal_places=2)

    class Meta:
        model = models.DragonpayTransaction
        fields = (
            "hashed_id",
            "type",
            "channel",
            "reference_number",
            "amount",
            "addon_fee",
            "channel_fee",
            "total_amount",
            "total_amount_paid",
            "description",
            "status",
            "error_message",
            "settlement_date",
            "created_at",
            "updated_at",
        )


class BukasTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.BukasTransaction
        fields = (
            "hashed_id",
            "type",
            "transaction_id",
            "reference_code",
            "amount",
            "status",
            "error_message",
            "transaction",
            "created_at",
            "updated_at",
        )


class BukasTransactionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.BukasTransaction
        fields = ("hashed_id", "soa")


class OverTheCounterTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.OverTheCounterTransaction
        fields = (
            "hashed_id",
            "type",
            "bank",
            "status",
            "error_message",
            "amount",
            "created_at",
            "updated_at",
        )


class CashierTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CashierTransaction
        fields = (
            "hashed_id",
            "type",
            "status",
            "error_message",
            "amount",
            "created_at",
            "updated_at",
        )


class PaymentTransactionPolymorphicSerializer(PolymorphicSerializer):
    model_serializer_mapping = {
        models.PaymentTransaction: PaymentTransactionSerializer,
        models.DragonpayTransaction: DragonpayTransactionSerializer,
        models.BukasTransaction: BukasTransactionSerializer,
        models.OverTheCounterTransaction: OverTheCounterTransactionSerializer,
        models.CashierTransaction: CashierTransactionSerializer,
    }


class StatementLineListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        data = data.filter(category__isnull=False)
        return super().to_representation(data)


class RootStatementLineListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        data = data.filter(category__isnull=True)
        return super().to_representation(data)


class StatementLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.StatementLine
        list_serializer_class = StatementLineListSerializer
        fields = ("description", "value", "created_at")


class RootStatementLineSerializer(serializers.ModelSerializer):
    class Meta(StatementLineSerializer.Meta):
        list_serializer_class = RootStatementLineListSerializer


class StatementLineCategorySerializer(serializers.ModelSerializer):
    lines = StatementLineSerializer(many=True)

    class Meta:
        model = models.StatementLineCategory
        fields = ("label", "lines")


class AccountTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.AccountTransaction
        fields = ("description", "amount", "created_at")


class StatementOfAccountSerializer(serializers.ModelSerializer):
    lines = RootStatementLineSerializer(many=True)
    payments = serializers.SerializerMethodField()
    categories = StatementLineCategorySerializer(many=True)
    transactions = AccountTransactionSerializer(many=True)

    remaining_balance = serializers.DecimalField(
        source="get_remaining_balance", max_digits=9, decimal_places=2
    )
    min_amount_due = serializers.DecimalField(
        source="get_min_amount_due", max_digits=9, decimal_places=2
    )
    available_credits = serializers.DecimalField(
        source="get_available_credits", max_digits=9, decimal_places=2
    )

    class Meta:
        model = models.StatementOfAccount
        fields = (
            "id",
            "user",
            "total_amount",
            "remaining_balance",
            "min_amount_due",
            "min_amount_due_date",
            "available_credits",
            "lines",
            "categories",
            "transactions",
            "payments",
            "updated_at",
        )

    def get_payments(self, obj):
        payments = obj.payments.order_by("-id")
        return PaymentTransactionPolymorphicSerializer(payments, many=True).data


class DragonpaySettlementReportSerializer(serializers.Serializer):
    file = serializers.FileField()


class PaymentSettlementListApiSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PaymentSettlement
        fields = (
            "settlement_id",
            "jv_number",
            "payment_method",
            "status",
            "error_message",
            "settled",
            "skipped",
            "invalid",
            "total",
            "created_at",
        )


class PaymentSettlementCreateApiSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PaymentSettlement
        fields = ("file", "jv_number", "payment_method")


class JournalVoucherListApiSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.JournalVoucher
        fields = (
            "file_id",
            "status",
            "error_message",
            "success",
            "invalid",
            "total",
            "created_at",
        )


class JournalVoucherCreateApiSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.JournalVoucher
        fields = ("file",)


class DragonpayTransactionListApiSerializer(serializers.ModelSerializer):
    StudentSerializer = inline_serializer_class(
        model=Student,
        fields=("id_number", "name"),
        name=serializers.SerializerMethodField(),
        get_name=lambda _, obj: f"{obj.first_name} {obj.last_name}",
    )
    DragonpayChannelSerializer = inline_serializer_class(
        model=models.DragonpayChannel,
        fields=("id", "description", "addon_percentage", "addon_fixed"),
    )
    SchoolSerializer = inline_serializer_class(
        model=models.School, fields=("id", "name")
    )

    student = serializers.SerializerMethodField()
    channel = DragonpayChannelSerializer()
    school = SchoolSerializer(source="get_school")

    class Meta:
        model = models.DragonpayTransaction
        fields = (
            "hashed_id",
            "jv_number",
            "type",
            "student",
            "channel",
            "reference_number",
            "amount",
            "addon_fee",
            "channel_fee",
            "total_amount",
            "total_amount_paid",
            "description",
            "status",
            "settlement_date",
            "school",
            "created_at",
            "updated_at",
        )

    def get_student(self, obj) -> StudentSerializer:
        student = obj.soa.user.student
        return self.StudentSerializer(student).data


class BukasTransactionListApiSerializer(serializers.ModelSerializer):
    StudentSerializer = inline_serializer_class(
        model=Student,
        fields=("id_number", "name"),
        name=serializers.SerializerMethodField(),
        get_name=lambda _, obj: f"{obj.first_name} {obj.last_name}",
    )
    SchoolSerializer = inline_serializer_class(
        model=models.School, fields=("id", "name")
    )

    student = serializers.SerializerMethodField()
    school = SchoolSerializer(source="get_school")

    class Meta:
        model = models.BukasTransaction
        fields = (
            "hashed_id",
            "type",
            "student",
            "transaction_id",
            "reference_code",
            "amount",
            "status",
            "transaction",
            "school",
            "created_at",
            "updated_at",
        )

    def get_student(self, obj) -> StudentSerializer:
        student = obj.soa.user.student
        return self.StudentSerializer(student).data


class OtcTransactionListApiSerializer(serializers.ModelSerializer):
    StudentSerializer = inline_serializer_class(
        model=Student,
        fields=("id_number", "name"),
        name=serializers.SerializerMethodField(),
        get_name=lambda _, obj: f"{obj.first_name} {obj.last_name}",
    )
    SchoolSerializer = inline_serializer_class(
        model=models.School, fields=("id", "name")
    )

    student = serializers.SerializerMethodField()
    school = SchoolSerializer(source="get_school")

    class Meta:
        model = models.OverTheCounterTransaction
        fields = (
            "payment_id",
            "bank",
            "amount",
            "status",
            "error_message",
            "student",
            "school",
            "settled_at",
            "created_at",
        )

    def get_student(self, obj) -> StudentSerializer:
        student = obj.soa.user.student
        return self.StudentSerializer(student).data


class CashierTransactionListApiSerializer(serializers.ModelSerializer):
    StudentSerializer = inline_serializer_class(
        model=Student,
        fields=("id_number", "name"),
        name=serializers.SerializerMethodField(),
        get_name=lambda _, obj: f"{obj.first_name} {obj.last_name}",
    )
    CashierSerializer = inline_serializer_class(
        model=User,
        fields=("name",),
        name=serializers.SerializerMethodField(),
        get_name=lambda _, obj: f"{obj.first_name} {obj.last_name}",
    )
    SoaSerializer = inline_serializer_class(
        model=models.StatementOfAccount,
        fields=("total_amount", "min_amount", "min_amount_due"),
        min_amount_due=serializers.DecimalField(
            source="get_min_amount_due", max_digits=9, decimal_places=2
        ),
    )
    SchoolSerializer = inline_serializer_class(
        model=models.School, fields=("id", "name")
    )

    student = serializers.SerializerMethodField()
    soa = SoaSerializer()
    processed_by = CashierSerializer()
    school = SchoolSerializer(source="get_school")

    class Meta:
        model = models.CashierTransaction
        fields = (
            "payment_id",
            "jv_number",
            "amount",
            "receipt_id",
            "status",
            "error_message",
            "student",
            "soa",
            "processed_by",
            "processed_at",
            "remarks",
            "school",
        )

    def get_student(self, obj) -> StudentSerializer:
        student = obj.soa.user.student
        return self.StudentSerializer(student).data


class CashierTransactionUpdateApiSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CashierTransaction
        fields = ("remarks", "amount", "receipt_id", "status")


class CashierTransactionPaidApiSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=9, decimal_places=2)
    receipt_id = serializers.CharField()
    remarks = serializers.CharField(required=False, allow_blank=True)


class CashierTransactionVoidApiSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=False, allow_blank=True)


class PaymentCountPerSchoolSerializer(serializers.ModelSerializer):
    bukas_count = serializers.SerializerMethodField()
    dragonpay_count = serializers.SerializerMethodField()
    over_the_counter_count = serializers.SerializerMethodField()
    cashier_count = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = (
            "code",
            "name",
            "bukas_count",
            "dragonpay_count",
            "over_the_counter_count",
            "cashier_count",
        )

    def get_bukas_count(self, obj) -> int:
        year_level = self.context["year_level"]
        semester = current_semester_get()

        bukas_transactions = models.BukasTransaction.objects.filter(
            soa__enrollment__semester=semester,
            soa__enrollment__student__course__school=obj,
        )

        # TODO: Custom filterclass for year_level
        if year_level and year_level.isnumeric():
            bukas_transactions = bukas_transactions.filter(
                soa__enrollment__year_level=year_level
            )

        return bukas_transactions.count()

    def get_dragonpay_count(self, obj) -> int:
        year_level = self.context["year_level"]
        semester = current_semester_get()

        bukas_transactions = models.DragonpayTransaction.objects.filter(
            soa__enrollment__semester=semester,
            soa__enrollment__student__course__school=obj,
        )

        # TODO: Custom filterclass for year_level
        if year_level and year_level.isnumeric():
            bukas_transactions = bukas_transactions.filter(
                soa__enrollment__year_level=year_level
            )

        return bukas_transactions.count()

    def get_over_the_counter_count(self, obj) -> int:
        year_level = self.context["year_level"]
        semester = current_semester_get()

        bukas_transactions = models.OverTheCounterTransaction.objects.filter(
            soa__enrollment__semester=semester,
            soa__enrollment__student__course__school=obj,
        )

        # TODO: Custom filterclass for year_level
        if year_level and year_level.isnumeric():
            bukas_transactions = bukas_transactions.filter(
                soa__enrollment__year_level=year_level
            )

        return bukas_transactions.count()

    def get_cashier_count(self, obj) -> int:
        year_level = self.context["year_level"]
        semester = current_semester_get()

        bukas_transactions = models.CashierTransaction.objects.filter(
            soa__enrollment__semester=semester,
            soa__enrollment__student__course__school=obj,
        )

        # TODO: Custom filterclass for year_level
        if year_level and year_level.isnumeric():
            bukas_transactions = bukas_transactions.filter(
                soa__enrollment__year_level=year_level
            )

        return bukas_transactions.count()


class OverTheCounterStatusPerSchoolSerializer(serializers.ModelSerializer):

    over_the_counter_count = serializers.SerializerMethodField()
    paid_over_the_counter_count = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = (
            "code",
            "name",
            "over_the_counter_count",
            "paid_over_the_counter_count",
        )

    def get_over_the_counter_count(self, obj) -> int:
        year_level = self.context["year_level"]
        semester = current_semester_get()

        over_the_counter_transactions = models.OverTheCounterTransaction.objects.filter(
            soa__enrollment__semester=semester,
            soa__enrollment__student__course__school=obj,
            status=models.OverTheCounterTransaction.Statuses.PENDING,
        )

        # TODO: Custom filterclass for year_level
        if year_level and year_level.isnumeric():
            over_the_counter_transactions = over_the_counter_transactions.filter(
                soa__enrollment__year_level=year_level
            )

        return over_the_counter_transactions.count()

    def get_paid_over_the_counter_count(self, obj) -> int:
        year_level = self.context["year_level"]
        semester = current_semester_get()

        paid_over_the_counter_transactions = (
            models.OverTheCounterTransaction.objects.filter(
                soa__enrollment__semester=semester,
                soa__enrollment__student__course__school=obj,
                status=models.OverTheCounterTransaction.Statuses.SETTLED,
            )
        )

        # TODO: Custom filterclass for year_level
        if year_level and year_level.isnumeric():
            paid_over_the_counter_transactions = (
                paid_over_the_counter_transactions.filter(
                    soa__enrollment__year_level=year_level
                )
            )

        return paid_over_the_counter_transactions.count()


class PaymentStatusPerSchoolSerializer(serializers.ModelSerializer):

    remaining_balance = serializers.SerializerMethodField()
    fully_paid = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = (
            "code",
            "name",
            "remaining_balance",
            "fully_paid",
        )

    def get_remaining_balance(self, obj) -> int:
        year_level = self.context["year_level"]

        remaining_balance = models.StatementOfAccount.objects.filter(
            enrollment__student__course__school=obj,
            has_remaining_balance=True,
        )

        # TODO: Custom filterclass for year_level
        if year_level and year_level.isnumeric():
            remaining_balance = remaining_balance.filter(
                enrollment__year_level=year_level
            )

        return remaining_balance.count()

    def get_fully_paid(self, obj) -> int:
        year_level = self.context["year_level"]

        fully_paid = models.StatementOfAccount.objects.filter(
            enrollment__student__course__school=obj,
            has_remaining_balance=False,
        )

        # TODO: Custom filterclass for year_level
        if year_level and year_level.isnumeric():
            fully_paid = fully_paid.filter(enrollment__year_level=year_level)

        return fully_paid.count()


class RevenuePerMethodPerSchoolYearSerializer(serializers.ModelSerializer):

    bukas_revenue = serializers.SerializerMethodField()
    dragonpay_revenue = serializers.SerializerMethodField()
    cashier_revenue = serializers.SerializerMethodField()
    otc_revenue = serializers.SerializerMethodField()

    class Meta:
        model = AcademicYear
        fields = (
            "year_start",
            "year_end",
            "bukas_revenue",
            "dragonpay_revenue",
            "cashier_revenue",
            "otc_revenue",
        )

    def get_bukas_revenue(self, obj):
        year_level = self.context["year_level"]

        bukas_transactions = models.BukasTransaction.objects.filter(
            soa__enrollment__semester__academic_year=obj,
        )

        # TODO: Custom filterclass for year_level
        if year_level and year_level.isnumeric():
            bukas_transactions = bukas_transactions.filter(
                soa__enrollment__year_level=year_level
            )

        bukas_transactions = bukas_transactions.aggregate(Sum("amount")).get(
            "amount__sum"
        )

        return bukas_transactions or 0

    def get_dragonpay_revenue(self, obj):
        year_level = self.context["year_level"]

        dragon_transactions = models.DragonpayTransaction.objects.filter(
            soa__enrollment__semester__academic_year=obj,
        )

        # TODO: Custom filterclass for year_level
        if year_level and year_level.isnumeric():
            dragon_transactions = dragon_transactions.filter(
                soa__enrollment__year_level=year_level
            )

        dragon_transactions = dragon_transactions.aggregate(Sum("amount")).get(
            "amount__sum"
        )

        return dragon_transactions or 0

    def get_cashier_revenue(self, obj):
        year_level = self.context["year_level"]

        cashier_transactions = models.CashierTransaction.objects.filter(
            soa__enrollment__semester__academic_year=obj,
        )

        # TODO: Custom filterclass for year_level
        if year_level and year_level.isnumeric():
            cashier_transactions = cashier_transactions.filter(
                soa__enrollment__year_level=year_level
            )

        cashier_transactions = cashier_transactions.aggregate(Sum("amount")).get(
            "amount__sum"
        )

        return cashier_transactions or 0

    def get_otc_revenue(self, obj):
        year_level = self.context["year_level"]

        otc_transactions = models.OverTheCounterTransaction.objects.filter(
            soa__enrollment__semester__academic_year=obj,
        )

        # TODO: Custom filterclass for year_level
        if year_level and year_level.isnumeric():
            otc_transactions = otc_transactions.filter(
                soa__enrollment__year_level=year_level
            )

        otc_transactions = otc_transactions.aggregate(Sum("amount")).get("amount__sum")

        return otc_transactions or 0


class StudentCashierTransactionUpdateApiSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CashierTransaction
        fields = ("status",)


class StudentOTCTransactionUpdateApiSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.OverTheCounterTransaction
        fields = ("status",)
