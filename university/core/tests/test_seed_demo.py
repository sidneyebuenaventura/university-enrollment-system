from collections import Counter
from decimal import Decimal
from io import StringIO
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command

from university.core.accounts.constants import ReservedRole
from university.core.accounts.models import Semester
from university.core.accounts.selectors import current_semester_get, next_semester_get
from university.core.cms.models import ClassSchedule
from university.core.demo.seed import DEMO_PASSWORD
from university.core.students.models import EnrolledClass, Enrollment, EnrollmentGrade
from university.core.students.selectors import (
    enrollment_get_latest_enrolled,
    enrollment_subjects_list,
)
from university.framework.events import EventBus
from university.payment.models import OverTheCounterTransaction

User = get_user_model()


@pytest.fixture
def publish():
    with mock.patch.object(EventBus, "publish") as publish:
        yield publish


@pytest.fixture
def seeded(db, publish, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    call_command("seed_demo", students=10, stdout=StringIO())


@pytest.mark.usefixtures("seeded")
class TestSeedDemo:
    def test_first_semester_is_running_and_second_is_next(self):
        assert current_semester_get().term == Semester.Terms.FIRST_SEMESTER
        assert next_semester_get().term == Semester.Terms.SECOND_SEMESTER

    def test_admin_account(self):
        admin = User.objects.get(username="admin")

        assert admin.check_password(DEMO_PASSWORD)
        assert admin.is_superuser
        assert admin.groups.filter(name=ReservedRole.SUPER_ADMIN).exists()

    def test_demo_student_can_enroll_for_next_semester(self):
        user = User.objects.get(username="student")
        student = user.student
        latest = enrollment_get_latest_enrolled(user=user)

        assert user.check_password(DEMO_PASSWORD)
        assert user.groups.filter(name=ReservedRole.STUDENT_ENROLLMENT).exists()
        assert latest.semester == current_semester_get()
        assert latest.statement_of_account.get_remaining_balance() == 0
        assert not student.enrollments.filter(semester=next_semester_get()).exists()

        passed = EnrolledClass.objects.filter(
            student=student, grades__status=EnrollmentGrade.GradingStatuses.PASSED
        ).values_list("curriculum_subject_id", flat=True)
        subjects = enrollment_subjects_list(
            student=student, passed_curr_subj_ids=list(passed)
        )
        assert subjects.exists()
        assert not subjects.filter(id__in=passed).exists()

    def test_finished_terms_are_graded_and_paid(self):
        current = current_semester_get()
        upcoming = next_semester_get()
        finished = Enrollment.objects.exclude(semester__in=[current, upcoming])

        assert finished.exists()
        for enrollment in finished:
            balance = enrollment.statement_of_account.get_remaining_balance()
            grade = enrollment.grade.grading_status

            assert enrollment.status == Enrollment.Statuses.ENROLLED
            assert grade == EnrollmentGrade.GradingStatuses.PASSED
            # SQLite sums decimals as floats and can leave a tiny remainder
            assert balance < Decimal("0.01")

    def test_rooms_are_not_double_booked(self):
        bookings = Counter(
            ClassSchedule.objects.values_list(
                "klass__semester", "room", "day", "time_in"
            )
        )

        assert bookings
        assert max(bookings.values()) == 1

    def test_transfers_waiting_for_validation(self):
        waiting = OverTheCounterTransaction.objects.filter(
            status=OverTheCounterTransaction.Statuses.FOR_VALIDATION
        )

        assert waiting.exists()
        assert any(transfer.is_overdue for transfer in waiting)
        assert all(transfer.receipt for transfer in waiting)

    def test_no_events_are_published(self, publish):
        publish.assert_not_called()

    def test_refuses_to_run_twice(self):
        with pytest.raises(CommandError):
            call_command("seed_demo", stdout=StringIO())
