from decimal import Decimal

from university.core.students.models import Enrollment, GradeFields, GradeStates
from university.framework.events import GenericModelEvent

from .students.services import (
    enrollment_enrolled,
    grade_sheet_process,
    grade_sheet_publish,
)


def handle_payment_success(event: GenericModelEvent):
    transaction = event.object.get_from_db()

    if not transaction:
        return

    soa = transaction.soa
    enrollment = soa.enrollment
    total_paid = Decimal(0)

    for payment in soa.payments.all():
        if payment.is_successful() or payment.is_settled():
            total_paid += payment.amount

    if (
        total_paid >= soa.min_amount
        and enrollment.status != Enrollment.Statuses.ENROLLED
    ):
        enrollment_enrolled(enrollment=soa.enrollment)


def handle_grade_sheet_created(event: GenericModelEvent):
    grade_sheet = event.object.get_from_db()
    grade_sheet_process(grade_sheet=grade_sheet)


def handle_grade_sheet_drafted(event: GenericModelEvent):
    grade_sheet = event.object.get_from_db()
    fields = GradeFields.values
    grade_sheet_publish(grade_sheet=grade_sheet, state=GradeStates.DRAFT, fields=fields)


def handle_grade_sheet_submitted(event: GenericModelEvent):
    grade_sheet = event.object.get_from_db()
    fields = event.data.get("fields", [])
    grade_sheet_publish(
        grade_sheet=grade_sheet, state=GradeStates.SUBMITTED, fields=fields
    )
