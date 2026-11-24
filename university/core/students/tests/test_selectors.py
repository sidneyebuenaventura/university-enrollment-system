from decimal import Decimal

import pytest
from rest_framework import exceptions

from university.core.accounts.tests.factories import AcademicYearFactory
from university.core.cms.tests.factories import ClassFactory, SubjectFactory
from university.core.students import selectors
from university.core.students.models import (
    Enrollment,
    EnrollmentGrade,
    GradeStatuses,
)
from university.core.students.tests.factories import (
    EnrolledClassFactory,
    EnrollmentFactory,
)
from university.payment.tests.factories import StatementOfAccountFactory

ENROLLED = Enrollment.Statuses.ENROLLED


def add_class(enrollment, units):
    return EnrolledClassFactory(
        enrollment=enrollment, klass=ClassFactory(subject=SubjectFactory(units=units))
    )


@pytest.mark.django_db
class TestEnrollmentLookups:
    def test_latest_is_by_academic_year(self, student):
        EnrollmentFactory(
            student=student, academic_year=AcademicYearFactory(year_start=2024)
        )
        latest = EnrollmentFactory(
            student=student, academic_year=AcademicYearFactory(year_start=2025)
        )

        assert selectors.enrollment_get_latest(user=student.user) == latest

    def test_latest_raises_when_student_has_no_enrollment(self, student):
        assert selectors.enrollment_get_latest(user=student.user) is None

        with pytest.raises(exceptions.NotFound):
            selectors.enrollment_get_latest(user=student.user, raise_exception=True)

    def test_latest_enrolled_skips_other_statuses(self, student):
        enrolled = EnrollmentFactory(student=student, status=ENROLLED)
        EnrollmentFactory(student=student, status=Enrollment.Statuses.ENROLLMENT)

        assert selectors.enrollment_get_latest_enrolled(user=student.user) == enrolled

    def test_for_payment_only_returns_enrollment_status(self, student):
        EnrollmentFactory(student=student, status=ENROLLED)
        assert selectors.enrollment_get_for_payment(user=student.user) is None

        enrollment = EnrollmentFactory(
            student=student, status=Enrollment.Statuses.ENROLLMENT
        )
        assert selectors.enrollment_get_for_payment(user=student.user) == enrollment


@pytest.mark.django_db
class TestEnrollmentUnits:
    def test_total_units(self, base_enrollment):
        add_class(base_enrollment, 3)
        add_class(base_enrollment, Decimal("1.5"))

        assert selectors.enrollment_total_units_get(enrollment=base_enrollment) == 4.5

    def test_latest_enrolled_total_units(self, student):
        enrollment = EnrollmentFactory(student=student, status=ENROLLED)
        add_class(enrollment, 3)
        add_class(enrollment, 2)

        units = selectors.enrollment_latest_enrolled_total_units_get(user=student.user)
        assert units == 5

    def test_latest_enrolled_total_units_without_enrollment(self, student):
        units = selectors.enrollment_latest_enrolled_total_units_get(user=student.user)
        assert units == 0


@pytest.mark.django_db
class TestGradedUnits:
    @pytest.fixture
    def enrollment(self, base_enrollment, enrolled_class_grade_factory):
        passed = add_class(base_enrollment, 3)
        failed = add_class(base_enrollment, 2)
        add_class(base_enrollment, 4)
        enrolled_class_grade_factory(enrolled_class=passed)
        enrolled_class_grade_factory(
            enrolled_class=failed, status=GradeStatuses.FAILED, final_grade=60
        )
        return base_enrollment

    def test_passed_units(self, enrollment):
        assert selectors.student_enrollment_passed_units_get(enrollment=enrollment) == 3

    def test_failed_units(self, enrollment):
        assert selectors.student_enrollment_failed_units_get(enrollment=enrollment) == 2

    def test_curriculum_subject_is_completed(
        self, enrollment, curriculum_subject_factory
    ):
        passed, failed, ungraded = enrollment.enrolled_classes.order_by("id")

        def is_completed(enrolled_class):
            curriculum_subject = curriculum_subject_factory(
                subject=enrolled_class.klass.subject
            )
            return selectors.enrollment_curriculum_subject_is_completed(
                enrollment=enrollment, curriculum_subject=curriculum_subject
            )

        assert is_completed(passed)
        assert not is_completed(failed)
        assert not is_completed(ungraded)


@pytest.mark.django_db
class TestEnrollmentBlocks:
    def test_has_failed_subject(self, student, enrollment_grade_factory):
        enrollment = EnrollmentFactory(student=student, status=ENROLLED)
        assert not selectors.student_has_failed_subject_get(student=student)

        enrollment_grade_factory(
            enrollment=enrollment,
            grading_status=EnrollmentGrade.GradingStatuses.FAILED,
        )
        enrollment.refresh_from_db()
        assert selectors.student_has_failed_subject_get(student=student)

    def test_has_remaining_balance(self, student, account_transaction_factory):
        soa = StatementOfAccountFactory(
            enrollment=EnrollmentFactory(student=student, status=ENROLLED)
        )
        account_transaction_factory(soa=soa, amount=Decimal("5000.00"))
        assert selectors.student_has_remaining_balance_get(user=student.user)

        account_transaction_factory(soa=soa, amount=Decimal("-5000.00"))
        assert not selectors.student_has_remaining_balance_get(user=student.user)

    def test_new_student_is_not_blocked(self, student):
        assert not selectors.student_has_failed_subject_get(student=student)
        assert not selectors.student_has_remaining_balance_get(user=student.user)
