from decimal import Decimal
from random import randint

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.utils import timezone
from rest_framework import exceptions

from university.core.accounts.models import School, Semester
from university.core.students.selectors import (
    enrollment_get_for_payment,
)

from .models import (
    BukasTransaction,
    CashierTransaction,
    DragonpayChannel,
    DragonpayTransaction,
    OverTheCounterTransaction,
    PaymentTransaction,
    StatementOfAccount,
)

User = get_user_model()


def soa_get_for_payment(*, user: User, raise_exception: bool = False):
    enrollment = enrollment_get_for_payment(user=user, raise_exception=True)

    try:
        soa = enrollment.statement_of_account
    except StatementOfAccount.DoesNotExist:
        if raise_exception:
            raise exceptions.NotFound("No Statement of Account for payment.") from None
        else:
            return None

    return soa


def soa_get_latest(*, user: User, raise_exception: bool = False):
    try:
        soa = (
            StatementOfAccount.objects.filter(user=user, enrollment__isnull=False)
            .order_by(
                "-enrollment__academic_year__year_start",
                "-enrollment__year_level",
                "-enrollment__semester__order",
            )
            .first()
        )
    except StatementOfAccount.DoesNotExist:
        if raise_exception:
            raise exceptions.NotFound("No Statement of Acccount found.") from None
        else:
            return None

    return soa


def soa_get_paid_amount(*, soa: StatementOfAccount) -> Decimal:
    total = Decimal(0)

    for payment in soa.payments.all():
        if payment.is_successful():
            total += payment.amount or Decimal(0)

    return total


def soa_get_settled_amount(*, soa: StatementOfAccount) -> Decimal:
    total = Decimal(0)

    for payment in soa.payments.all():
        if payment.is_settled():
            total += payment.amount or Decimal(0)

    return total


def soa_get_min_amount_due(*, soa: StatementOfAccount) -> Decimal:
    result = soa.transactions.filter(amount__lt=0).aggregate(sum=Sum("amount"))
    paid = abs(result.get("sum") or Decimal(0))

    amount_due = soa.min_amount - paid

    if amount_due > 0:
        return amount_due

    return Decimal(0)


def soa_get_remaining_balance(*, soa: StatementOfAccount) -> Decimal:
    result = soa.transactions.aggregate(sum=Sum("amount"))
    balance = result.get("sum") or Decimal(0)
    has_remaining_balance = balance > 0

    if soa.has_remaining_balance != has_remaining_balance:
        soa.has_remaining_balance = has_remaining_balance
        soa.save()

    return max(balance, Decimal(0))


def soa_get_available_credits(*, soa: StatementOfAccount) -> Decimal:
    result = soa.transactions.aggregate(sum=Sum("amount"))
    balance = result.get("sum") or Decimal(0)

    if balance < 0:
        return abs(balance)

    return Decimal(0)


def dragonpay_channel_get(
    *, channel_id: int, raise_exception: bool = False
) -> DragonpayChannel:
    obj = DragonpayChannel.objects.filter(id=channel_id).first()

    if not obj and raise_exception:
        raise exceptions.NotFound("No enrollment for payment.")

    return obj


def transaction_get_from_hash(
    *, hashed_id: str, raise_exception: bool = False, lock: bool = False
) -> PaymentTransaction:
    pk = PaymentTransaction.decode_hashed_id(hashed_id)

    if not pk:
        if raise_exception:
            raise exceptions.NotFound("Transaction not found.")
        else:
            return

    if lock:
        qs = PaymentTransaction.objects.select_for_update()
    else:
        qs = PaymentTransaction.objects.all()

    obj = qs.filter(pk=pk).first()

    if not obj and raise_exception:
        raise exceptions.NotFound("Transaction not found.")

    return obj


def otc_transaction_get_pending(
    *, soa: StatementOfAccount
) -> OverTheCounterTransaction:
    return (
        OverTheCounterTransaction.objects.filter(
            soa=soa, status=OverTheCounterTransaction.Statuses.PENDING
        )
        .order_by("-id")
        .first()
    )


def cashier_transaction_get_pending(*, soa: StatementOfAccount) -> CashierTransaction:
    return (
        CashierTransaction.objects.filter(
            soa=soa, status=CashierTransaction.Statuses.PENDING
        )
        .order_by("-id")
        .first()
    )


def cashier_transaction_get(
    *, payment_id: str, raise_exception: bool = False, lock: bool = False
) -> CashierTransaction:
    if lock:
        qs = CashierTransaction.objects.select_for_update()
    else:
        qs = CashierTransaction.objects.all()

    obj = qs.filter(payment_id=payment_id).first()

    if not obj and raise_exception:
        raise exceptions.NotFound("Cashier transaction not found.")

    return obj


def dragonpay_settlement_test_csv_generate() -> list[dict]:
    transactions = DragonpayTransaction.objects.filter(
        status=DragonpayTransaction.Statuses.SUCCESS
    )
    now = timezone.now()
    rows = []

    for transaction in transactions:
        student = transaction.soa.user.student
        date_format = "%-m/%d/%y %-I:%M %p"
        description = (
            f"{student.id_number} : "
            f"{student.last_name.upper()}, {student.first_name.upper()}. : "
            f"Payment for Midtern 1st Semester 2022-23"
        )
        rows.append(
            {
                "Create Date": transaction.created_at.strftime(date_format).lower(),
                "Settle Date": now.strftime(date_format).lower(),
                "Refno": transaction.reference_number,
                "Merchant Txn Id": transaction.payment_id,
                "Ccy": "PHP",
                "Amount": transaction.total_amount_paid,
                "Fee": transaction.addon_fee + transaction.channel_fee,
                "Settlement": transaction.amount,
                "Proc": transaction.channel.proc_id,
                "Description": description,
            }
        )

    return rows


def cashier_settlement_test_csv_generate() -> list:
    transactions = CashierTransaction.objects.filter(
        status=CashierTransaction.Statuses.PAID
    )
    rows = []

    for transaction in transactions:
        student = transaction.soa.user.student

        change = transaction.amount % 100
        cash = transaction.amount + (100 - change)
        is_new = randint(1, 5) == 3

        data = {
            "IDNO": student.id_number,
            "LASTNAME": student.last_name,
            "FIRSTNAME": student.first_name,
            "MID_NAME": student.middle_name,
            "SECTION": "",
            "LEVEL": transaction.soa.enrollment.year_level,
            "CUSTOMER": "",
            "ACCNT_NO": 4,
            "EXPL": "Tuition and other fees",
            "REFERENCE": transaction.receipt_id,
            "DATE": transaction.created_at.strftime("%m/%d/%Y"),
            "CHK_AMT": Decimal("0.00"),
            "CASH": cash,
            "AMOUNT": transaction.amount,
            "BATCH": "501004",
            "TRANSF": "",
            "DIV": "00",
            "CUST_NO": "CASH",
            "CO": "11",
            "CC": "000",
            "GLNO": "115010",
            "BIRTHDATE": "",
            "FATHER": "",
            "MOTHER": "",
            "NEW": "",
        }

        if is_new:
            if student.birth_date:
                data["BIRTHDATE"] = student.birth_date.strftime("%m/%d/%Y")

            data["FATHER"] = "NA"
            data["MOTHER"] = "NA"
            data["NEW"] = "Y"

        rows.append(data)

    return rows


def journal_voucher_test_csv_generate() -> list:
    transactions = OverTheCounterTransaction.objects.filter(
        status=OverTheCounterTransaction.Statuses.PENDING,
    )
    rows = []

    now = timezone.now()
    base_jv_number = 100000
    base_date = timezone.make_aware(timezone.datetime(2022, 7, 30))
    delta = now - base_date
    jv_number = f"JV{base_jv_number + delta.days}"
    settled_at = now.strftime("%m/%d/%Y")

    for transaction in transactions:
        student = transaction.soa.user.student
        amount = transaction.soa.get_min_amount_due()
        description = (
            f"{transaction.bank}-{transaction.created_at.strftime('%m.%d.%Y')}"
        )

        if amount == 0:
            amount = randint(2000, 5000)

        rows.append(
            [
                student.id_number,
                -abs(amount),
                description,
                jv_number,
                settled_at,
            ]
        )

    return rows


def bukas_transaction_total_revenue_get(
    schools: list[School],
    semester: Semester,
    year_level: int = None,
):
    bukas_transactions = BukasTransaction.objects.filter(
        soa__enrollment__semester=semester,
        soa__enrollment__student__course__school__in=schools,
    )

    # TODO: Custom filterclass for year_level
    if year_level and year_level.isnumeric():
        bukas_transactions = bukas_transactions.filter(
            soa__enrollment__year_level=year_level
        )
    bukas_transaction_total = bukas_transactions.aggregate(Sum("amount")).get(
        "amount__sum"
    )

    return bukas_transaction_total or 0


def dragonpay_transaction_total_revenue_get(
    schools: list[School],
    semester: Semester,
    year_level: int = None,
):
    dragonpay_transactions = DragonpayTransaction.objects.filter(
        soa__enrollment__semester=semester,
        soa__enrollment__student__course__school__in=schools,
    )

    # TODO: Custom filterclass for year_level
    if year_level and year_level.isnumeric():
        dragonpay_transactions = dragonpay_transactions.filter(
            soa__enrollment__year_level=year_level
        )
    dragonpay_transaction_total = dragonpay_transactions.aggregate(Sum("amount")).get(
        "amount__sum"
    )

    return dragonpay_transaction_total or 0


def cashier_transaction_total_revenue_get(
    schools: list[School],
    semester: Semester,
    year_level: int = None,
):
    cashier_transactions = CashierTransaction.objects.filter(
        soa__enrollment__semester=semester,
        soa__enrollment__student__course__school__in=schools,
    )

    # TODO: Custom filterclass for year_level
    if year_level and year_level.isnumeric():
        cashier_transactions = cashier_transactions.filter(
            soa__enrollment__year_level=year_level
        )
    cashier_transaction_total = cashier_transactions.aggregate(Sum("amount")).get(
        "amount__sum"
    )

    return cashier_transaction_total or 0


def otc_transaction_total_revenue_get(
    schools: list[School],
    semester: Semester,
    year_level: int = None,
):
    otc_transactions = OverTheCounterTransaction.objects.filter(
        soa__enrollment__semester=semester,
        soa__enrollment__student__course__school__in=schools,
    )

    # TODO: Custom filterclass for year_level
    if year_level and year_level.isnumeric():
        otc_transactions = otc_transactions.filter(
            soa__enrollment__year_level=year_level
        )
    otc_transaction_total = otc_transactions.aggregate(Sum("amount")).get("amount__sum")

    return otc_transaction_total or 0


def total_revenue_get(
    schools: list[School],
    semester: Semester,
    year_level: int = None,
):
    bukas_total = bukas_transaction_total_revenue_get(
        schools=schools, semester=semester, year_level=year_level
    )
    dragonpay_total = dragonpay_transaction_total_revenue_get(
        schools=schools, semester=semester, year_level=year_level
    )
    cashier_total = cashier_transaction_total_revenue_get(
        schools=schools, semester=semester, year_level=year_level
    )
    otc_total = otc_transaction_total_revenue_get(
        schools=schools, semester=semester, year_level=year_level
    )

    total_revenue = bukas_total + dragonpay_total + cashier_total + otc_total

    return total_revenue


def otc_transaction_count_get(
    semester: Semester,
    year_level: int = None,
):
    otc_transactions = OverTheCounterTransaction.objects.filter(
        soa__enrollment__semester=semester,
    )

    # TODO: Custom filterclass for year_level
    if year_level and year_level.isnumeric():
        otc_transactions = otc_transactions.filter(
            soa__enrollment__year_level=year_level
        )

    return otc_transactions.count()


def cashier_transaction_count_get(
    semester: Semester,
    year_level: int = None,
):
    cashier_transactions = CashierTransaction.objects.filter(
        soa__enrollment__semester=semester,
    )

    # TODO: Custom filterclass for year_level
    if year_level and year_level.isnumeric():
        cashier_transactions = cashier_transactions.filter(
            soa__enrollment__year_level=year_level
        )

    return cashier_transactions.count()


def dragonpay_transaction_count_get(
    semester: Semester,
    year_level: int = None,
):
    dragonpay_transactions = DragonpayTransaction.objects.filter(
        soa__enrollment__semester=semester,
    )

    # TODO: Custom filterclass for year_level
    if year_level and year_level.isnumeric():
        dragonpay_transactions = dragonpay_transactions.filter(
            soa__enrollment__year_level=year_level
        )

    return dragonpay_transactions.count()


def bukas_transaction_count_get(
    semester: Semester,
    year_level: int = None,
):
    bukas_transactions = BukasTransaction.objects.filter(
        soa__enrollment__semester=semester,
    )

    # TODO: Custom filterclass for year_level
    if year_level and year_level.isnumeric():
        bukas_transactions = bukas_transactions.filter(
            soa__enrollment__year_level=year_level
        )

    return bukas_transactions.count()


def payment_method_percentage_get(
    semester: Semester,
    year_level: int = None,
):

    bukas_count = bukas_transaction_count_get(semester=semester, year_level=year_level)
    dragonpay_count = dragonpay_transaction_count_get(
        semester=semester, year_level=year_level
    )
    cashier_count = cashier_transaction_count_get(
        semester=semester, year_level=year_level
    )
    otc_count = otc_transaction_count_get(semester=semester, year_level=year_level)

    total_payment = bukas_count + dragonpay_count + cashier_count + otc_count

    bukas_percentage = (
        (bukas_count / total_payment) * 100 if bukas_count != 0 else bukas_count
    )
    dragonpay_percentage = (
        (dragonpay_count / total_payment) * 100
        if dragonpay_count != 0
        else dragonpay_count
    )
    cashier_percentage = (
        (cashier_count / total_payment) * 100 if cashier_count != 0 else cashier_count
    )
    otc_percentage = (otc_count / total_payment) * 100 if otc_count != 0 else otc_count

    return {
        "bukas": round(bukas_percentage, 2),
        "dragonpay": round(dragonpay_percentage, 2),
        "cashier": round(cashier_percentage, 2),
        "otc": round(otc_percentage, 2),
    }
