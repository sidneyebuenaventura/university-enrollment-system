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
    AddSubjectRequest,
    ChangeScheduleRequest,
    EnrolledClass,
    Enrollment,
    EnrollmentEvent,
    EnrollmentGrade,
    EnrollmentStatus,
    OpenClassRequest,
    StudentRequestTypes,
    WithdrawalRequest,
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


@pytest.mark.django_db
class TestStudentRequestCreate:
    @pytest.mark.parametrize(
        "request_type, model",
        [
            (StudentRequestTypes.CHANGE_SCHEDULE, ChangeScheduleRequest),
            (StudentRequestTypes.ADD_SUBJECT, AddSubjectRequest),
            (StudentRequestTypes.OPEN_CLASS, OpenClassRequest),
            (StudentRequestTypes.PARTIAL_WITHDRAWAL, WithdrawalRequest),
        ],
    )
    def test_creates_request_with_history(self, student, request_type, model):
        data = {"type": request_type, "detail": "MATH 101", "reason": "Conflict"}

        result = services.student_request_create(student=student, data=data)

        request = model.objects.get(student=student)
        assert result == {"request_no": request.request_no}
        history = request.review_histories.get()
        assert history.user == student.user
        assert history.status == "Pending"

    def test_full_withdrawal_category(self, student):
        data = {
            "type": StudentRequestTypes.FULL_WITHDRAWAL,
            "detail": "All subjects",
            "reason": "Moving abroad",
        }

        services.student_request_create(student=student, data=data)

        request = WithdrawalRequest.objects.get(student=student)
        assert request.category == WithdrawalRequest.Categories.FULL_WITHDRAWAL


@pytest.mark.django_db
class TestStudentRequestUpdate:
    def test_approved_change_schedule_notifies_student(
        self, change_schedule_request, staff_user, publish
    ):
        request = services.change_schedule_request_update(
            request=change_schedule_request,
            user=staff_user,
            data={"status": ChangeScheduleRequest.Statuses.APPROVED, "remarks": "OK"},
        )

        history = request.review_histories.get()
        assert history.user == staff_user
        assert history.status == "Approved"
        assert history.remarks == "OK"
        publish.assert_called_once_with(
            events.REQUEST_CHANGE_SCHEDULE_APPROVED, object=request, remarks="OK"
        )

    def test_in_review_add_subject_does_not_notify(
        self, add_subject_request, staff_user, publish
    ):
        services.add_subject_request_update(
            request=add_subject_request,
            user=staff_user,
            data={"status": AddSubjectRequest.Statuses.INREVIEW, "remarks": ""},
        )

        add_subject_request.refresh_from_db()
        assert add_subject_request.status == AddSubjectRequest.Statuses.INREVIEW
        publish.assert_not_called()

    def test_open_class_for_approval(self, open_class_request, staff_user, publish):
        data = {"status": OpenClassRequest.Statuses.FOR_APPROVAL, "remarks": "Noted"}

        services.open_class_request_update(
            request=open_class_request, user=staff_user, data=data
        )
        publish.assert_called_once_with(
            events.REQUEST_OPEN_CLASS_FOR_APPROVAL,
            object=open_class_request,
            remarks="Noted",
        )

        # Another review without a status change only notifies when asked to
        publish.reset_mock()
        services.open_class_request_update(
            request=open_class_request, user=staff_user, data=data
        )
        publish.assert_not_called()

        services.open_class_request_update(
            request=open_class_request,
            user=staff_user,
            data={**data, "notify_student": True},
        )
        publish.assert_called_once_with(
            events.REQUEST_OPEN_CLASS_REVIEW_UPDATED,
            object=open_class_request,
            remarks="Noted",
        )
        assert open_class_request.review_histories.count() == 3

    def test_encoded_withdrawal_notifies_student(
        self, withdrawal_request, staff_user, publish
    ):
        services.withdrawal_request_update(
            request=withdrawal_request,
            user=staff_user,
            data={"status": WithdrawalRequest.Statuses.ENCODED, "remarks": "Done"},
        )

        publish.assert_called_once_with(
            events.REQUEST_WITHDRAWAL_APPROVED,
            object=withdrawal_request,
            remarks="Done",
            request_type="Partial Withdrawal",
            request_description="Partial Withdrawal request",
            status="Encoded",
            prev_status="Pending",
        )
