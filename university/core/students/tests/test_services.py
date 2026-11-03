from decimal import Decimal
from unittest import mock

import pytest
from rest_framework import exceptions

from university.core import events
from university.core.accounts.constants import ReservedRole
from university.core.accounts.tests.factories import (
    AcademicYearFactory,
    SemesterFactory,
)
from university.core.cms.tests.factories import ClassFactory
from university.core.students import services
from university.core.students.models import (
    EnrolledClass,
    Enrollment,
    EnrollmentEvent,
    EnrollmentGrade,
    EnrollmentStatus,
)
from university.core.students.tests.factories import EnrollmentFactory
from university.payment.tests.factories import StatementOfAccountFactory

Statuses = Enrollment.Statuses
Steps = Enrollment.Steps
BlockStatuses = EnrollmentStatus.BlockStatuses


@pytest.fixture(autouse=True)
def publish():
    with mock.patch.object(services.event_publisher, "generic") as generic:
        yield generic


@pytest.mark.django_db
class TestEnrollmentCreate:
    @pytest.fixture
    def current_year(self):
        return AcademicYearFactory(year_start=2025)

    @pytest.fixture
    def next_semester(self, current_year):
        with (
            mock.patch.object(services, "current_academic_year_get") as current,
            mock.patch.object(services, "next_semester_get") as next_semester,
        ):
            current.return_value = current_year

            def set_next_semester(academic_year):
                semester = SemesterFactory(academic_year=academic_year)
                next_semester.return_value = semester
                return semester

            yield set_next_semester

    def test_first_enrollment_starts_at_year_one(
        self, student, current_year, next_semester
    ):
        semester = next_semester(current_year)

        enrollment = services.enrollment_create(student=student, data={})

        assert enrollment.year_level == 1
        assert enrollment.semester == semester
        assert enrollment.academic_year == current_year
        assert enrollment.status == Statuses.ENROLLMENT
        assert enrollment.discounts

    def test_same_academic_year_keeps_year_level(
        self, student, current_year, next_semester
    ):
        EnrollmentFactory(
            student=student,
            academic_year=current_year,
            year_level=2,
            status=Statuses.ENROLLED,
        )
        next_semester(current_year)

        enrollment = services.enrollment_create(student=student, data={})

        assert enrollment.year_level == 2

    def test_new_academic_year_moves_up_a_level(
        self, student, current_year, next_semester
    ):
        EnrollmentFactory(
            student=student,
            academic_year=current_year,
            year_level=2,
            status=Statuses.ENROLLED,
        )
        next_semester(AcademicYearFactory(year_start=2026))

        enrollment = services.enrollment_create(student=student, data={})

        assert enrollment.year_level == 3


@pytest.mark.django_db
class TestEnrollmentUpdate:
    @pytest.fixture
    def enrollment(self, base_enrollment):
        base_enrollment.status = Statuses.ENROLLMENT
        base_enrollment.step = Steps.START
        base_enrollment.save()
        return base_enrollment

    def test_enrolled_cannot_be_updated(self, enrollment):
        enrollment.status = Statuses.ENROLLED
        enrollment.save()

        with pytest.raises(exceptions.PermissionDenied):
            services.enrollment_update(
                enrollment=enrollment, data={"step": Steps.INFORMATION}
            )

    def test_payment_step_not_allowed_during_pre_enrollment(self, enrollment):
        enrollment.status = Statuses.PRE_ENROLLMENT
        enrollment.save()

        with pytest.raises(exceptions.PermissionDenied):
            services.enrollment_update(
                enrollment=enrollment, data={"step": Steps.PAYMENT}
            )

    def test_information_updates_student(self, enrollment):
        data = {
            "step": Steps.INFORMATION,
            "contact_number": "09170000001",
            "institutional_email": "juan@university.test",
            "father_name": "Pedro Santos",
        }

        services.enrollment_update(enrollment=enrollment, data=data)
        services.enrollment_update(enrollment=enrollment, data=data)

        enrollment.refresh_from_db()
        student = enrollment.student
        student.refresh_from_db()
        assert enrollment.step == Steps.INFORMATION
        assert enrollment.contact_number == "09170000001"
        assert student.phone_no == "09170000001"
        assert student.father_name == "Pedro Santos"
        assert student.user.email == "juan@university.test"
        assert enrollment.events.get().event == (
            EnrollmentEvent.Events.ENROLLMENT_STARTED
        )

    def test_discounts(self, enrollment, personnel, student_factory):
        sibling = student_factory()
        data = {
            "step": Steps.DISCOUNTS,
            "is_employee": True,
            "employee_no": personnel.user.username,
            "is_employee_dependent": False,
            "is_working_scholar": True,
            "has_enrolled_sibling": True,
            "sibling_student_numbers": [sibling.id_number],
        }

        services.enrollment_update(enrollment=enrollment, data=data)

        enrollment.refresh_from_db()
        discount = enrollment.discounts
        assert enrollment.step == Steps.DISCOUNTS
        assert discount.is_employee
        assert discount.personnel == personnel
        assert discount.is_working_scholar
        assert list(discount.siblings.all()) == [sibling]

    def test_subjects_reserve_classes_and_build_statement(
        self, enrollment, curriculum_subject_factory
    ):
        classes = [ClassFactory(), ClassFactory()]
        EnrolledClass.objects.create(enrollment=enrollment, klass=ClassFactory())
        data = {
            "step": Steps.SUBJECTS,
            "enrolled_classes": [
                {
                    "klass": klass,
                    "curriculum_subject": curriculum_subject_factory(
                        subject=klass.subject
                    ),
                }
                for klass in classes
            ],
        }

        services.enrollment_update(enrollment=enrollment, data=data)

        enrollment.refresh_from_db()
        assert enrollment.step == Steps.SUBJECTS
        assert {ec.klass for ec in enrollment.enrolled_classes.all()} == set(classes)
        assert not enrollment.enrolled_classes.exclude(
            status=EnrolledClass.Statuses.RESERVED
        ).exists()
        assert enrollment.statement_of_account


@pytest.mark.django_db
def test_enrollment_enrolled(base_enrollment, role_factory, publish):
    role = role_factory(name=ReservedRole.STUDENT_ENROLLMENT)
    user = base_enrollment.student.user
    user.groups.add(role)

    services.enrollment_enrolled(enrollment=base_enrollment)

    base_enrollment.refresh_from_db()
    assert base_enrollment.status == Statuses.ENROLLED
    assert not user.groups.filter(pk=role.pk).exists()
    publish.assert_called_once_with(events.ENROLLMENT_ENROLLED, object=base_enrollment)


@pytest.mark.django_db
class TestEnrollmentStatusEvaluate:
    @pytest.fixture
    def previous(self, student):
        return StatementOfAccountFactory(
            enrollment=EnrollmentFactory(
                student=student,
                status=Statuses.ENROLLED,
                academic_year=AcademicYearFactory(year_start=2024),
            )
        )

    @pytest.fixture
    def enrollment(self, student):
        return EnrollmentFactory(
            student=student,
            status=Statuses.PRE_ENROLLMENT,
            academic_year=AcademicYearFactory(year_start=2025),
        )

    def test_new_student_is_pre_enrolled(self, enrollment):
        services.enrollment_status_evaluate(enrollment=enrollment)

        enrollment.refresh_from_db()
        assert enrollment.status == Statuses.PRE_ENROLLED
        assert enrollment.statement_of_account
        assert enrollment.enrollmentstatus.block_status == BlockStatuses.PASSED

    def test_outstanding_balance_blocks(
        self, enrollment, previous, account_transaction_factory
    ):
        account_transaction_factory(soa=previous, amount=Decimal("5000.00"))

        services.enrollment_status_evaluate(enrollment=enrollment)

        enrollment.refresh_from_db()
        status = enrollment.enrollmentstatus
        assert enrollment.status == Statuses.PRE_ENROLLMENT
        assert status.block_status == BlockStatuses.BLOCKED_WITH_OUTSTANDING_BALANCE
        assert status.is_for_manual_tagging
        assert not hasattr(enrollment, "statement_of_account")

    def test_failed_subject_blocks(
        self, enrollment, previous, enrollment_grade_factory
    ):
        enrollment_grade_factory(
            enrollment=previous.enrollment,
            grading_status=EnrollmentGrade.GradingStatuses.FAILED,
        )

        services.enrollment_status_evaluate(enrollment=enrollment)

        enrollment.refresh_from_db()
        assert enrollment.status == Statuses.PRE_ENROLLMENT
        assert (
            enrollment.enrollmentstatus.block_status
            == BlockStatuses.BLOCKED_WITH_FAILED_SUBJECT
        )

    def test_credits_carry_over(
        self, enrollment, previous, account_transaction_factory
    ):
        account_transaction_factory(soa=previous, amount=Decimal("5000.00"))
        account_transaction_factory(soa=previous, amount=Decimal("-5500.00"))

        services.enrollment_status_evaluate(enrollment=enrollment)

        enrollment.refresh_from_db()
        assert previous.get_available_credits() == 0
        assert enrollment.statement_of_account.get_available_credits() == Decimal(
            "500.00"
        )
