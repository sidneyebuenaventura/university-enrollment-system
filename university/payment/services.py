import csv
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Union

import botocore.exceptions
import structlog
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from django.db import transaction as db_transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.timezone import make_aware
from rest_framework import exceptions
from sentry_sdk import capture_exception

from university.core.cms.models import Discount, Subject
from university.core.cms.selectors import laboratory_fee_get
from university.core.students.models import Enrollment, EnrollmentEvent, Student
from university.core.students.services import enrollment_step_4_payments
from university.framework.events import event_publisher
from university.payment import tasks

from . import events
from .clients import BukasClient, DragonpayClient
from .models import (
    AccountTransaction,
    BukasTransaction,
    CashierTransaction,
    DragonpayKey,
    DragonpayTransaction,
    JournalVoucher,
    OverTheCounterTransaction,
    PaymentMethods,
    PaymentSettlement,
    PaymentTransaction,
    StatementOfAccount,
)
from .selectors import (
    cashier_transaction_get_pending,
    otc_transaction_get_pending,
    soa_get_latest,
)

log = structlog.get_logger(__name__)

User = get_user_model()

bukas_client = BukasClient()
dragonpay_client = DragonpayClient()


def dragonpay_payment_create(*, transaction: DragonpayTransaction):
    amount = f"{transaction.total_amount:.2f}"
    key = DragonpayKey.objects.filter(school=transaction.get_school()).first()
    url = dragonpay_client.create_payment(
        amount,
        transaction_id=transaction.hashed_id,
        proc_id=transaction.channel.proc_id,
        merchant_id=key.merchant_id,
        merchant_password=key.merchant_password,
    )
    return url


def dragonpay_transaction_create(*, soa: StatementOfAccount, data: dict):
    key = DragonpayKey.objects.filter(school=soa.get_school()).first()

    if not key:
        raise exceptions.ValidationError("No available payment gateway.")

    amount = Decimal(data.get("amount"))
    min_amount_due = soa.get_min_amount_due()

    if min_amount_due > 0 and amount < min_amount_due:
        raise exceptions.ValidationError(
            {"amount": "Amount is less than minimum amount due"}
        )

    channel = data.get("channel")
    addon_fee = channel.addon_fixed
    channel_fee = Decimal(0)

    if channel.addon_percentage:
        percentage = Decimal(1 - (channel.addon_percentage / 100))
        amount_with_fee = (amount + addon_fee) / percentage
        channel_fee = amount_with_fee - addon_fee - amount

    with db_transaction.atomic():
        transaction = DragonpayTransaction.objects.create(
            soa=soa,
            channel=channel,
            amount=amount,
            addon_fee=addon_fee,
            channel_fee=channel_fee,
        )
        transaction.generate_id()
        enrollment_step_4_payments(
            enrollment=soa.enrollment, data={"step": Enrollment.Steps.PAYMENT}
        )

    url = dragonpay_payment_create(transaction=transaction)
    return {"redirect_url": url}


def dragonpay_transaction_update(*, transaction: DragonpayTransaction, data: dict):
    status = data.get("status")
    status_changed = transaction.status != status

    # TODO: Verify digest to ensure data is legit. Can't trust data from URL query string.
    transaction.reference_number = data.get("refno")
    transaction.description = data.get("message")
    transaction.status = status
    transaction.meta = data
    transaction.save()

    if status_changed:
        return transaction.status


def bukas_payment_failed(*, transaction: BukasTransaction):
    pass  # Do something if it fails. Notification?


def bukas_payment_success(*, transaction: BukasTransaction):
    event_publisher.generic(events.PAYMENT_SUCCESS, object=transaction)


def bukas_transaction_status_update(*, transaction: BukasTransaction, status: str):
    status_actions = {
        BukasTransaction.Statuses.FAILED: bukas_payment_failed,
        BukasTransaction.Statuses.FOR_FUNDING: bukas_payment_success,
    }
    action = status_actions.get(status)

    if action:
        action(transaction=transaction)


def bukas_transaction_update(*, transaction: BukasTransaction, data: dict):
    status_map = {
        "For Funding": BukasTransaction.Statuses.FOR_FUNDING,
        "Disbursed": BukasTransaction.Statuses.DISBURSED,
    }
    status = status_map.get(data.get("status"))
    status_changed = transaction.status != status

    # TODO: Verify digest to ensure data is legit. Can't trust data from URL query string.
    transaction.transaction_id = data.get("transaction_id")
    transaction.reference_code = data.get("reference_code")
    transaction.amount = data.get("amount")
    transaction.transaction = data
    transaction.status = status
    transaction.save()

    if status_changed:
        bukas_transaction_status_update(transaction=transaction, status=status)


def bukas_payment_create(*, transaction: BukasTransaction):
    soa = transaction.soa
    enrollment = soa.enrollment
    student = enrollment.student
    course = enrollment.student.course
    days_in_arrears = (timezone.now() - soa.min_amount_due_date).days

    payment_data = {
        "course": course.name,
        "current_due_total": float(soa.min_amount),
        "date_due": soa.min_amount_due_date.strftime("%Y-%m-%d"),
        "days_in_arrears": days_in_arrears if days_in_arrears > 0 else 0,
        "degree": course.get_category_display(),
        "email_address": student.user.email,
        "first_name": student.first_name,
        "last_name": student.last_name,
        "mobile_number": soa.enrollment.student.phone_no,
        "school": settings.UNIVERSITY_NAME,
        "school_remaining_balance": float(soa.get_remaining_balance()),
        "student_id_number": student.id_number,
        "year": enrollment.year_level,
    }
    response = bukas_client.create_payment(payment_data)

    if response.status_code != 200:
        log.error("bukas_payment_create_failed", response=response.content)
        transaction.status = BukasTransaction.Statuses.FAILED
        transaction.save()
        raise exceptions.APIException("Failed to create bukas payment")

    enrollment_step_4_payments(
        enrollment=soa.enrollment, data={"step": Enrollment.Steps.PAYMENT}
    )
    return response.content.decode()


def bukas_transaction_create(*, soa: StatementOfAccount, data: dict):
    with db_transaction.atomic():
        transaction = BukasTransaction.objects.create(soa=soa)
        transaction.generate_id()

    url = f"{settings.UNIVERSITY_PAYMENT_SERVICE}/transactions/{transaction.hashed_id}/"
    return {"redirect_url": url}


def otc_transaction_create(*, soa: StatementOfAccount, data: dict):
    transaction = otc_transaction_get_pending(soa=soa)

    if not transaction:
        with db_transaction.atomic():
            transaction = OverTheCounterTransaction.objects.create(
                soa=soa, bank=data.get("bank")
            )
            transaction.generate_id()

        eta = timezone.now() + settings.UNIVERSITY_PAYMENT_TRANSACTION_TTL
        tasks.async_payment_transaction_expire.apply_async((transaction.id,), eta=eta)

    return {"reference_number": transaction.hashed_id, "bank": data.get("bank")}


def cashier_transaction_create(*, soa: StatementOfAccount, data: dict):
    transaction = cashier_transaction_get_pending(soa=soa)

    if not transaction:
        with db_transaction.atomic():
            transaction = CashierTransaction.objects.create(soa=soa)
            transaction.generate_id()

        eta = timezone.now() + settings.UNIVERSITY_PAYMENT_TRANSACTION_TTL
        tasks.async_payment_transaction_expire.apply_async((transaction.id,), eta=eta)

    return {"reference_number": transaction.hashed_id}


def cashier_transaction_tag_as_paid(
    *,
    transaction: CashierTransaction,
    cashier: User = None,
    **data,
):
    if transaction.status != CashierTransaction.Statuses.PENDING:
        raise exceptions.PermissionDenied

    for field, value in data.items():
        setattr(transaction, field, value)

    transaction.status = CashierTransaction.Statuses.PAID
    transaction.processed_at = timezone.now()
    transaction.processed_by = cashier
    transaction.save()


def cashier_transaction_void(
    *, transaction: CashierTransaction, remarks: str = "", cashier: User = None
):
    if transaction.status not in CashierTransaction.SUCCESS_STATUSES:
        raise exceptions.PermissionDenied

    transaction.status = CashierTransaction.Statuses.VOIDED
    transaction.remarks = remarks
    transaction.save()


def payment_create(*, user: User, data: dict):
    soa = soa_get_latest(user=user, raise_exception=True)

    methods = {
        PaymentMethods.DRAGONPAY.value: dragonpay_transaction_create,
        PaymentMethods.BUKAS.value: bukas_transaction_create,
        PaymentMethods.OTC.value: otc_transaction_create,
        PaymentMethods.CASHIER.value: cashier_transaction_create,
    }
    method = methods.get(data.get("payment_method"))

    if method:
        return method(soa=soa, data=data)


def payment_settlement_create(
    *, file: File, payment_method: PaymentMethods, jv_number: str = ""
) -> PaymentSettlement:
    settlement = PaymentSettlement.objects.create(
        file=file, payment_method=payment_method, jv_number=jv_number
    )
    settlement.generate_id()
    tasks.async_payment_settlement_process.delay(settlement.id)
    return settlement


def _dragonpay_settlement_process(*, data: dict, jv_number: str = "") -> str:
    with db_transaction.atomic():
        transaction = DragonpayTransaction.objects.filter(
            payment_id=data.get("Merchant Txn Id"),
            reference_number=data.get("Refno"),
        ).first()

        if not transaction:
            return "invalid"

        if transaction.status == DragonpayTransaction.Statuses.SETTLED:
            return "skipped"

        AccountTransaction.objects.get_or_create(
            soa=transaction.soa,
            ref_id=transaction.id,
            defaults={
                "student": transaction.soa.enrollment.student,
                "amount": -transaction.amount,
                "description": "Dragonpay payment",
                "jv_number": jv_number,
                "ref": transaction,
            },
        )

        try:
            settlement_date = make_aware(
                datetime.strptime(data["Settle Date"], "%m/%d/%y %I:%M %p")
            )
        except ValueError:
            settlement_date = timezone.now()

        enrollment = transaction.soa.enrollment
        enrollment.events.get_or_create(event=EnrollmentEvent.Events.ENROLLMENT_ENDED)

        transaction.jv_number = jv_number
        transaction.status = DragonpayTransaction.Statuses.SETTLED
        transaction.settlement_date = settlement_date
        transaction.save()

    event_publisher.generic(events.PAYMENT_SETTLED, object=transaction)
    return "settled"


def _cashier_settlement_process(*, data: dict, jv_number: str = "") -> str:
    with db_transaction.atomic():
        student_id = data.get("IDNO")
        receipt_id = data.get("REFERENCE")
        amount = data.get("AMOUNT")

        transaction = CashierTransaction.objects.filter(
            soa__user__student__id_number=student_id, receipt_id=receipt_id
        ).first()

        if not transaction:
            return "invalid"

        if transaction.status == CashierTransaction.Statuses.SETTLED:
            return "skipped"

        AccountTransaction.objects.get_or_create(
            soa=transaction.soa,
            ref_id=transaction.id,
            defaults={
                "student": transaction.soa.enrollment.student,
                "amount": -abs(Decimal(amount)),
                "description": "Cashier payment",
                "jv_number": jv_number,
                "ref": transaction,
            },
        )

        enrollment = transaction.soa.enrollment
        enrollment.events.get_or_create(event=EnrollmentEvent.Events.ENROLLMENT_ENDED)

        transaction.jv_number = jv_number
        transaction.status = CashierTransaction.Statuses.SETTLED
        transaction.settled_at = timezone.now()
        transaction.save()

    event_publisher.generic(events.PAYMENT_SETTLED, object=transaction)
    return "settled"


def _payment_settlement_failed(*, payment_settlement: PaymentSettlement, error: str):
    payment_settlement.status = PaymentSettlement.Statuses.FAILED
    payment_settlement.error_message = error
    payment_settlement.save()


def payment_settlement_process(*, payment_settlement: PaymentSettlement):
    payment_settlement.status = PaymentSettlement.Statuses.PROCESSING
    payment_settlement.save()

    settlement_processors = {
        PaymentMethods.DRAGONPAY: _dragonpay_settlement_process,
        PaymentMethods.CASHIER: _cashier_settlement_process,
    }
    processor = settlement_processors.get(payment_settlement.payment_method)

    if not processor:
        _payment_settlement_failed(
            payment_settlement=payment_settlement,
            error="Settlement processor not implemented.",
        )
        return

    stats = {
        "settled": 0,
        "skipped": 0,
        "invalid": 0,
        "total": 0,
    }

    try:
        file_contents = payment_settlement.file.read()
        csv_data = file_contents.decode().split("\r\n")
        reader = csv.DictReader(csv_data)

        for row in reader:
            result = processor(data=row, jv_number=payment_settlement.jv_number)
            stats[result] += 1
            stats["total"] += 1
    except (UnicodeDecodeError, botocore.exceptions.ClientError) as error:
        _payment_settlement_failed(
            payment_settlement=payment_settlement,
            error="Error reading settlement file",
        )
        capture_exception(error)
        return

    payment_settlement.status = PaymentSettlement.Statuses.COMPLETED
    payment_settlement.settled = stats["settled"]
    payment_settlement.skipped = stats["skipped"]
    payment_settlement.invalid = stats["invalid"]
    payment_settlement.total = stats["total"]
    payment_settlement.save()


def journal_voucher_create(*, file: File) -> JournalVoucher:
    jv = JournalVoucher.objects.create(file=file)
    jv.generate_id()
    tasks.async_journal_voucher_process.delay(jv.id)
    return jv


def _journal_voucher_failed(*, journal_voucher: JournalVoucher, error: str):
    journal_voucher.status = JournalVoucher.Statuses.FAILED
    journal_voucher.error_message = error
    journal_voucher.save()


def _journal_voucher_bank_process(
    *,
    student: Student,
    amount: Decimal,
    description: str,
    jv_number: str,
    bank: OverTheCounterTransaction.Banks,
):
    transaction = OverTheCounterTransaction.objects.filter(
        soa__user__student=student,
        bank=bank,
        status=OverTheCounterTransaction.Statuses.PENDING,
    ).first()

    if not transaction:
        soa = soa_get_latest(user=student.user)
        transaction = OverTheCounterTransaction.objects.create(soa=soa, bank=bank)
        transaction.generate_id()

    with db_transaction.atomic():
        transaction.status = OverTheCounterTransaction.Statuses.SETTLED
        transaction.amount = abs(amount)
        transaction.jv_number = jv_number
        transaction.settled_at = timezone.now()
        transaction.save()

        AccountTransaction.objects.get_or_create(
            soa=transaction.soa,
            ref_id=transaction.id,
            defaults={
                "student": transaction.soa.enrollment.student,
                "amount": -abs(amount),
                "description": f"OTC Payment {description}",
                "jv_number": jv_number,
                "ref": transaction,
            },
        )

    event_publisher.generic(events.PAYMENT_SUCCESS, object=transaction)
    event_publisher.generic(events.PAYMENT_SETTLED, object=transaction)
    return "success"


def _journal_voucher_manual_adjustments(
    *, student: Student, amount: Decimal, description: str, jv_number: str
):
    soa = soa_get_latest(user=student.user)

    if not soa:
        return "invalid"

    AccountTransaction.objects.create(
        soa=soa,
        student=student,
        amount=-abs(amount),
        description=f"Adjustment {description}",
        jv_number=jv_number,
    )
    return "success"


def journal_voucher_process(*, journal_voucher: JournalVoucher):
    journal_voucher.status = JournalVoucher.Statuses.PROCESSING
    journal_voucher.save()

    stats = {
        "success": 0,
        "invalid": 0,
        "total": 0,
    }

    try:
        file_contents = journal_voucher.file.read()
        csv_data = file_contents.decode().split("\r\n")
        reader = csv.reader(csv_data)

        for row in reader:
            if not row:
                continue

            stats["total"] += 1

            if len(row) != 5:
                stats["invalid"] += 1
                continue

            id_number = row[0]
            amount = Decimal(row[1])
            description = row[2]
            jv_number = row[3]

            student = Student.objects.filter(id_number=id_number).first()

            if not student:
                stats["invalid"] += 1
                continue

            processor = _journal_voucher_manual_adjustments
            banks = [
                OverTheCounterTransaction.Banks.BDO,
                OverTheCounterTransaction.Banks.PNB,
                OverTheCounterTransaction.Banks.MBTC,
                OverTheCounterTransaction.Banks.LBP,
            ]
            kwargs = {}

            for bank in banks:
                if description.startswith(bank):
                    processor = _journal_voucher_bank_process
                    kwargs["bank"] = bank
                    break

            result = processor(
                student=student,
                amount=amount,
                description=description,
                jv_number=jv_number,
                **kwargs,
            )
            stats[result] += 1
    except (UnicodeDecodeError, botocore.exceptions.ClientError) as error:
        _journal_voucher_failed(
            journal_voucher=journal_voucher,
            error="Error reading journal voucher file",
        )
        capture_exception(error)
        return

    journal_voucher.status = JournalVoucher.Statuses.COMPLETED
    journal_voucher.success = stats["success"]
    journal_voucher.invalid = stats["invalid"]
    journal_voucher.total = stats["total"]
    journal_voucher.save()


def soa_create(
    *, enrollment: Enrollment, discount_auto_apply: bool = False, override: bool = False
):
    if hasattr(enrollment, "soa") and not override:
        return enrollment.soa

    student = enrollment.student
    academic_year = enrollment.academic_year
    course = student.course

    discount = None

    if hasattr(enrollment, "discounts"):
        discount = enrollment.discounts.validated_discount
        if discount:
            discount_fee_exemptions = discount.fee_exemptions.all()

    tf_pro_fee = Decimal(0)
    tf_pro_units = 0
    tf_non_pro_fee = Decimal(0)
    tf_non_pro_units = 0
    discount_rate_total = Decimal(0)

    subject_groups = []
    lab_fees = []

    for enrolled_class in enrollment.enrolled_classes.all():
        curriculum_subject = enrolled_class.curriculum_subject
        subject = Subject.objects.none
        klass = enrolled_class.klass

        tf_rate = klass.tuition_fee_rate if klass else None

        if not curriculum_subject:
            subject = enrolled_class.equivalent_subject
        else:
            subject = curriculum_subject.subject

        subject_groups.append(subject.grouping)
        lab_fee = laboratory_fee_get(academic_year=academic_year, subject=subject)

        if lab_fee:
            lab_fees.append(lab_fee)

        if tf_rate:
            rate = tf_rate.rate or Decimal(0)

            if subject.is_professional_subject:
                tf_pro_fee += rate * subject.units
                tf_pro_units += subject.units
            else:
                tf_non_pro_fee += rate * subject.units
                tf_non_pro_units += subject.units

            # NOTE: Check if subject is included for discounted tuition fee
            if (
                curriculum_subject
                and discount
                and discount.category_rate_exemption
                and curriculum_subject.category_rate
                not in discount.category_rate_exemption
            ):
                subject_fee = rate * subject.units
                print(
                    enrolled_class.klass.tuition_fee_rate.rate,
                    enrolled_class.klass.subject.units,
                    curriculum_subject.category_rate,
                )
                discount_rate_total += subject_fee

    # TODO: Revisit upon Fee Specification Clarification
    # total_units = tf_pro_units + tf_non_pro_units
    # misc_fees = miscellaneous_fees_get(
    #     academic_year=academic_year,
    #     curriculum_period=curriculum_period,
    #     total_units=total_units,
    # )
    # other_fees = Fee.objects.none()

    # for subject_group in set(subject_groups):
    #     other_fees = other_fees.union(
    #         other_fees_get(
    #             academic_year=academic_year,
    #             curriculum_period=curriculum_period,
    #             subject_group=subject_group,
    #             student=student,
    #             course=course,
    #         )
    #     )

    misc_fees = []
    other_fees = []

    if enrollment.miscellaneous_fee_specification:
        misc_fees = [
            fee for fee in enrollment.miscellaneous_fee_specification.fees.all()
        ]

    if enrollment.other_fee_specification:
        other_fees = [fee for fee in enrollment.other_fee_specification.fees.all()]

    misc_fee_total = Decimal(0)
    other_fee_total = Decimal(0)

    has_discount_exemption = discount and discount_fee_exemptions

    for mf in misc_fees:
        misc_fee_total += mf.amount

        if has_discount_exemption and mf not in discount_fee_exemptions:
            discount_rate_total += mf.amount

    for of in other_fees:
        other_fee_total += of.amount

        if has_discount_exemption and of not in discount_fee_exemptions:
            discount_rate_total += of.amount

    lab_fee_total = sum([lf.rate for lf in lab_fees])
    total_amount = sum(
        [
            tf_pro_fee,
            tf_non_pro_fee,
            lab_fee_total,
            misc_fee_total or Decimal(0),
            other_fee_total or Decimal(0),
        ]
    )

    min_amount_percentage = Decimal("0.35")

    soa, _ = StatementOfAccount.objects.update_or_create(
        user=student.user,
        enrollment=enrollment,
        defaults={
            "total_amount": total_amount,
            "min_amount": total_amount * min_amount_percentage,
            "min_amount_due_date": timezone.now() + timedelta(days=365),
        },
    )
    soa.lines.all().delete()
    soa.categories.all().delete()
    soa.transactions.all().delete()

    if tf_pro_fee:
        soa.lines.create(
            description=f"Tuition for Professional Subjects (Units: {tf_pro_units})",
            value=tf_pro_fee,
        )
        soa.transactions.create(
            student=student,
            description=f"Pro Subject TF {tf_pro_units} units",
            amount=tf_pro_fee,
        )

    if tf_non_pro_fee:
        soa.lines.create(
            description=f"Tuition for General Education (Units: {tf_non_pro_units})",
            value=tf_non_pro_fee,
        )
        soa.transactions.create(
            student=student,
            description=f"General Education TF {tf_non_pro_units} units",
            amount=tf_non_pro_fee,
        )

    if lab_fee_total:
        soa.lines.create(
            description="Laboratory Fees",
            value=lab_fee_total,
        )
        soa.transactions.create(
            student=student, description="Laboratory Fees", amount=lab_fee_total
        )

    if misc_fees:
        category, _ = soa.categories.get_or_create(label="Miscellaneous Fees")

        for fee in misc_fees:
            category.lines.create(
                soa=soa, description=fee.name, value=fee.amount, ref=fee
            )

        soa.transactions.create(
            student=student, description="Miscellaneous Fees", amount=misc_fee_total
        )

    if other_fees:
        category, _ = soa.categories.get_or_create(label="Other Fees")

        for fee in other_fees:
            category.lines.create(
                soa=soa, description=fee.name, value=fee.amount, ref=fee
            )

        soa.transactions.create(
            student=student, description="Other Fees", amount=other_fee_total
        )

    if discount and (
        (discount.type == Discount.Types.NORMAL and not discount_auto_apply)
        or (discount_auto_apply)
    ):
        total_discount = discount_rate_total * (discount.percentage / 100)

        soa.lines.create(
            description=f"Discount ({discount.name})",
            value=-abs(total_discount),
            ref=discount,
        )

        soa.transactions.create(
            student=student,
            description=f"Discount ({enrollment.discount.name})",
            amount=-abs(total_discount),
            ref=discount,
        )

    return soa


def payment_transaction_expire(
    *, transaction: Union[OverTheCounterTransaction, CashierTransaction]
):
    transaction.fail()
    transaction.error_message = (
        f"The generated reference #{transaction.payment_id} has already expired. "
        "Kindly generate a new reference number to be able to proceed with payment. "
        "Thank you."
    )
    transaction.save()
