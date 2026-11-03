from decimal import Decimal

import pytest
from rest_framework import exceptions

from university.core.accounts.tests.factories import AcademicYearFactory
from university.core.cms.tests.factories import ClassFactory, SubjectFactory
from university.core.students import selectors
from university.core.students.models import Enrollment
from university.core.students.tests.factories import (
    EnrolledClassFactory,
    EnrollmentFactory,
)

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
