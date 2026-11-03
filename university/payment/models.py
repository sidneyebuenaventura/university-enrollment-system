import uuid
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from hashids import Hashids

from university.core.accounts.models import School
from university.core.students.models import Enrollment, Student
from university.framework.models import (
    BaseModel,
    PolymorphicBaseModel,
    SoftDeleteModel,
    TextChoiceField,
)
from university.framework.validators import csv_file_validator

User = get_user_model()


class PaymentMethods(models.TextChoices):
    DRAGONPAY = "DP", "Dragonpay"
    BUKAS = "B", "Bukas"
    OTC = "OTC", "Bank"
    CASHIER = "C", "School Cashier"


class StatementOfAccount(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="statement_of_accounts",
    )
    enrollment = models.OneToOneField(
        Enrollment,
        on_delete=models.SET_NULL,
        null=True,
        related_name="statement_of_account",
    )
    total_amount = models.DecimalField(max_digits=9, decimal_places=2)
    min_amount = models.DecimalField(max_digits=9, decimal_places=2)
    min_amount_due_date = models.DateTimeField()
    has_remaining_balance = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user} - {self.total_amount}"

    def get_school(self):
        return self.enrollment.student.course.school

    def get_min_amount_due(self) -> Decimal:
        from .selectors import soa_get_min_amount_due

        return soa_get_min_amount_due(soa=self)

    def get_remaining_balance(self) -> Decimal:
        from .selectors import soa_get_remaining_balance

        return soa_get_remaining_balance(soa=self)

    def get_available_credits(self) -> Decimal:
        from .selectors import soa_get_available_credits

        return soa_get_available_credits(soa=self)


class StatementLineCategory(BaseModel):
    soa = models.ForeignKey(
        StatementOfAccount, on_delete=models.CASCADE, related_name="categories"
    )
    label = models.CharField(max_length=255)

    class Meta:
        verbose_name_plural = "Statement Line Categories"

    def __str__(self):
        return self.label


class StatementLine(BaseModel):
    soa = models.ForeignKey(
        StatementOfAccount, on_delete=models.CASCADE, related_name="lines"
    )
    category = models.ForeignKey(
        StatementLineCategory,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="lines",
    )
    description = models.CharField(max_length=255)
    value = models.DecimalField(max_digits=9, decimal_places=2)

    ref_ctype = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, blank=True, null=True
    )
    ref_id = models.PositiveIntegerField(null=True, blank=True)
    ref = GenericForeignKey("ref_ctype", "ref_id")

    def __str__(self):
        return self.description


class AccountTransaction(BaseModel):
    student = models.ForeignKey(Student, on_delete=models.PROTECT)
    soa = models.ForeignKey(
        StatementOfAccount,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="transactions",
    )

    amount = models.DecimalField(max_digits=9, decimal_places=2)
    description = models.TextField()
    jv_number = models.CharField(max_length=255, blank=True)

    ref_ctype = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, blank=True, null=True
    )
    ref_id = models.PositiveIntegerField(null=True, blank=True)
    ref = GenericForeignKey("ref_ctype", "ref_id")

    def __str__(self):
        return self.description


class PaymentTransaction(PolymorphicBaseModel):
    HASHIDS = Hashids(
        settings.HASHIDS_PAYMENT_SALT,
        min_length=settings.HASHIDS_MIN_LENGTH,
        alphabet=settings.HASHIDS_ALPHABET_DEFAULT,
    )

    payment_id = models.CharField(max_length=255, null=True)
    jv_number = models.CharField(max_length=255, blank=True)

    soa = models.ForeignKey(
        StatementOfAccount, on_delete=models.CASCADE, related_name="payments"
    )
    remarks = models.TextField(blank=True)
    error_message = models.TextField(blank=True)

    def __str__(self):
        return f"Payment: {self.soa}"

    @property
    def hashed_id(self):
        # TODO: remove deprecated field. use payment_id directly.
        return self.payment_id

    @classmethod
    def decode_hashed_id(cls, hashed_id):
        result = cls.HASHIDS.decode(hashed_id)
        if len(result) > 0:
            return result[0]

    @property
    def type(self):
        return "Generic Payment"

    def generate_id(self):
        self.payment_id = self.HASHIDS.encode(self.id)
        self.save()

    def is_successful(self):
        raise NotImplementedError

    def is_settled(self):
        raise NotImplementedError

    def get_school(self):
        return self.soa.enrollment.student.course.school


class DragonpayTransaction(PaymentTransaction):
    class Statuses(models.TextChoices):
        PENDING = "P", "Pending"
        FAILED = "F", "Failed"
        SUCCESS = "S", "Success"
        SETTLED = "ST", "Settled"

    channel = models.ForeignKey("DragonpayChannel", on_delete=models.PROTECT)
    status = TextChoiceField(
        max_length=2, choices_cls=Statuses, default=Statuses.PENDING
    )

    amount = models.DecimalField(max_digits=9, decimal_places=2)
    addon_fee = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    channel_fee = models.DecimalField(max_digits=9, decimal_places=2, default=0)

    reference_number = models.CharField(
        max_length=255, blank=True, null=True, db_index=True
    )
    description = models.TextField()
    settlement_date = models.DateTimeField(null=True, blank=True)

    meta = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"Dragonpay Payment: {self.soa}"

    @property
    def total_amount(self) -> Decimal:
        return self.amount + self.addon_fee

    @property
    def total_amount_paid(self) -> Decimal:
        return self.amount + self.addon_fee + self.channel_fee

    @property
    def type(self):
        return PaymentMethods.DRAGONPAY.label

    def is_successful(self):
        return self.status == self.Statuses.SUCCESS

    def is_settled(self):
        return self.status == self.Statuses.SETTLED


class DragonpayChannel(SoftDeleteModel):
    proc_id = models.CharField(max_length=25)
    description = models.TextField(help_text="Channel name")
    addon_percentage = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Merchant percentage charge",
    )
    addon_fixed = models.DecimalField(
        max_digits=9, decimal_places=2, default=0, help_text="Fixed institution charge"
    )

    def __str__(self):
        return self.description


class DragonpayKey(BaseModel):
    school = models.OneToOneField(School, on_delete=models.SET_NULL, null=True)
    merchant_id = models.CharField(max_length=255)
    merchant_password = models.CharField(max_length=255)

    def __str__(self):
        return str(self.school)


class BukasTransaction(PaymentTransaction):
    class Statuses(models.TextChoices):
        PENDING = "P", "Pending"
        FAILED = "F", "Failed"
        FOR_FUNDING = "FF", "For Funding"
        DISBURSED = "D", "Disbursed"

    transaction_id = models.CharField(
        max_length=255, db_index=True, blank=True, null=True
    )
    reference_code = models.CharField(
        max_length=255, db_index=True, blank=True, null=True
    )
    amount = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
    status = TextChoiceField(
        max_length=2, choices_cls=Statuses, default=Statuses.PENDING
    )
    transaction = models.JSONField(default=dict)

    def __str__(self):
        return f"Bukas Payment: {self.soa}"

    @property
    def type(self):
        return PaymentMethods.BUKAS.label

    def is_successful(self):
        return self.status == self.Statuses.FOR_FUNDING

    def is_settled(self):
        return self.status == self.Statuses.FOR_FUNDING


class OverTheCounterTransaction(PaymentTransaction):
    class Statuses(models.TextChoices):
        PENDING = "P", "Pending"
        FAILED = "F", "Failed"
        SUCCESS = "S", "Success"
        SETTLED = "SS", "Settled"

    class Banks(models.TextChoices):
        BDO = "BDO", "Banco de Oro"
        PNB = "PNB", "Philippine National Bank"
        MBTC = "MBTC", "Metrobank"
        LBP = "LBP", "Land Bank of the Philippines"

    bank = TextChoiceField(max_length=12, choices_cls=Banks)
    amount = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
    status = TextChoiceField(
        max_length=2, choices_cls=Statuses, default=Statuses.PENDING
    )
    settled_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"OTC Payment: {self.soa}"

    @property
    def type(self):
        return PaymentMethods.OTC.label

    def is_successful(self):
        return self.status == self.Statuses.SUCCESS

    def is_settled(self):
        return self.status == self.Statuses.SETTLED

    def fail(self):
        self.status = self.Statuses.FAILED


class CashierTransaction(PaymentTransaction):
    class Statuses(models.TextChoices):
        PENDING = "P", "Pending"
        FAILED = "F", "Failed"
        VOIDED = "V", "Voided"
        PAID = "S", "Paid"
        SETTLED = "SS", "Settled"

    FAILED_STATUSES = [Statuses.FAILED, Statuses.VOIDED]
    SUCCESS_STATUSES = [Statuses.PAID, Statuses.SETTLED]

    amount = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
    status = TextChoiceField(
        max_length=2, choices_cls=Statuses, default=Statuses.PENDING
    )
    receipt_id = models.CharField(max_length=255, blank=True)
    settled_at = models.DateTimeField(blank=True, null=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    processed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, blank=True, null=True
    )

    def __str__(self):
        return f"Cashier Payment: {self.soa}"

    @property
    def type(self):
        return PaymentMethods.CASHIER.label

    def is_successful(self):
        return self.status == self.Statuses.PAID

    def is_settled(self):
        return self.status == self.Statuses.SETTLED

    def fail(self):
        self.status = self.Statuses.FAILED


def payment_settlement_file_path(instance, filename):
    file_ext = filename.split(".")[-1]
    file_name = str(uuid.uuid4()).replace("-", "")
    return f"settlements/{file_name}.{file_ext}"


class PaymentSettlement(BaseModel):
    class Statuses(models.TextChoices):
        PENDING = "P", "Pending"
        PROCESSING = "O", "Processing"
        FAILED = "F", "Failed"
        COMPLETED = "C", "Completed"

    HASHIDS = Hashids(
        settings.HASHIDS_PAYMENT_SETTLEMENT_SALT,
        min_length=settings.HASHIDS_MIN_LENGTH,
        alphabet=settings.HASHIDS_ALPHABET_ALPHA_ONLY,
    )

    settlement_id = models.CharField(max_length=255, null=True)
    jv_number = models.CharField(max_length=255, blank=True)

    file = models.FileField(
        upload_to=payment_settlement_file_path, validators=[csv_file_validator]
    )
    payment_method = TextChoiceField(max_length=3, choices_cls=PaymentMethods)
    status = TextChoiceField(
        max_length=2, choices_cls=Statuses, default=Statuses.PENDING
    )
    error_message = models.TextField(blank=True)

    settled = models.IntegerField(default=0, help_text="Settled transactions")
    skipped = models.IntegerField(
        default=0, help_text="Skipped transactions that are already settled"
    )
    invalid = models.IntegerField(default=0, help_text="Transactions not found")
    total = models.IntegerField(default=0)

    def __str__(self):
        return f"Payment Settlement {self.settlement_id}"

    def generate_id(self):
        self.settlement_id = self.HASHIDS.encode(self.id)
        self.save()


def journal_voucher_file_path(instance, filename):
    file_ext = filename.split(".")[-1]
    file_name = str(uuid.uuid4()).replace("-", "")
    return f"journal_vouchers/{file_name}.{file_ext}"


class JournalVoucher(BaseModel):
    class Statuses(models.TextChoices):
        PENDING = "P", "Pending"
        PROCESSING = "O", "Processing"
        FAILED = "F", "Failed"
        COMPLETED = "C", "Completed"

    HASHIDS = Hashids(
        settings.HASHIDS_JOURNAL_VOUCHER_SALT,
        min_length=settings.HASHIDS_MIN_LENGTH,
        alphabet=settings.HASHIDS_ALPHABET_ALPHA_ONLY,
    )

    file_id = models.CharField(max_length=255, null=True)

    file = models.FileField(
        upload_to=journal_voucher_file_path, validators=[csv_file_validator]
    )
    status = TextChoiceField(
        max_length=2, choices_cls=Statuses, default=Statuses.PENDING
    )
    error_message = models.TextField(blank=True)

    success = models.IntegerField(default=0, help_text="Successful entries")
    invalid = models.IntegerField(
        default=0, help_text="Entries with student IDs not found"
    )
    total = models.IntegerField(default=0)

    def __str__(self):
        return f"Journal Voucher {self.file_id}"

    def generate_id(self):
        self.file_id = self.HASHIDS.encode(self.id)
        self.save()
