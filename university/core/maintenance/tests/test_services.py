from datetime import timedelta
from unittest import mock

import pytest
from django.utils import timezone

from university.core import events
from university.core.accounts.constants import MobileModule, ReservedRole
from university.core.maintenance import selectors, services
from university.core.students.models import Student


@pytest.fixture
def roles(role_factory):
    return {
        key: role_factory(name=key)
        for key in (
            ReservedRole.STUDENT,
            ReservedRole.STUDENT_PRE_ENROLLMENT,
            ReservedRole.STUDENT_ENROLLMENT,
        )
    }


@pytest.fixture
def make_student(student_factory, roles):
    def make(**kwargs):
        kwargs.setdefault("year_level", 1)
        kwargs.setdefault("status", Student.Statuses.REGULAR)
        student = student_factory(**kwargs)
        student.user.groups.add(roles[ReservedRole.STUDENT])
        return student

    return make


def has_role(student, key):
    return student.user.groups.filter(name=key).exists()


@pytest.mark.django_db
class TestScheduleStudents:
    def test_matches_year_level(self, make_student, enrollment_schedule_factory):
        first_year = make_student(year_level=1)
        make_student(year_level=2)

        schedule = enrollment_schedule_factory(year_level=1)

        students = selectors.enrollment_schedule_students_get(schedule=schedule)
        assert list(students) == [first_year]

    def test_filters_by_student_type_course_and_school(
        self, make_student, enrollment_schedule_factory, course_factory
    ):
        course = course_factory()
        match = make_student(course=course)
        make_student(course=course, status=Student.Statuses.SCHOLAR)
        make_student()

        schedule = enrollment_schedule_factory(
            student_type=Student.Statuses.REGULAR,
            course=course,
            school=course.school,
        )

        students = selectors.enrollment_schedule_students_get(schedule=schedule)
        assert list(students) == [match]

    def test_ignores_users_without_student_role(
        self, make_student, student_factory, enrollment_schedule_factory
    ):
        student = make_student()
        student_factory(year_level=1)

        schedule = enrollment_schedule_factory()

        students = selectors.enrollment_schedule_students_get(schedule=schedule)
        assert list(students) == [student]


@pytest.mark.django_db
class TestScheduleRoles:
    @pytest.mark.parametrize(
        "start, end, role",
        [
            (
                services.pre_enrollment_start,
                services.pre_enrollment_end,
                ReservedRole.STUDENT_PRE_ENROLLMENT,
            ),
            (
                services.enrollment_start,
                services.enrollment_end,
                ReservedRole.STUDENT_ENROLLMENT,
            ),
        ],
    )
    def test_start_and_end_toggle_role(
        self, make_student, enrollment_schedule_factory, start, end, role
    ):
        student = make_student(year_level=1)
        other = make_student(year_level=2)
        schedule = enrollment_schedule_factory(year_level=1)

        start(schedule=schedule)

        assert has_role(student, role)
        assert not has_role(other, role)

        end(schedule=schedule)

        assert not has_role(student, role)
        assert has_role(student, ReservedRole.STUDENT)

    def test_missing_role_is_skipped(self, student, enrollment_schedule_factory):
        schedule = enrollment_schedule_factory()

        services.enrollment_start(schedule=schedule)

        assert not student.user.groups.exists()


@pytest.mark.django_db
class TestScheduleWatchers:
    """A schedule that was already handled shouldn't stop the others."""

    def test_starting(self, enrollment_schedule_factory):
        handled = enrollment_schedule_factory()
        handled.events.create(event=events.ENROLLMENT_STARTED)
        pending = enrollment_schedule_factory()

        with mock.patch.object(
            services.tasks.enrollment_start, "apply_async"
        ) as apply_async:
            services.enrollment_starting_schedule_watch()

        apply_async.assert_called_once_with((pending.id,), eta=pending.start_datetime)
        assert pending.events.filter(event=events.ENROLLMENT_STARTED).exists()

    def test_ending(self, enrollment_schedule_factory):
        now = timezone.now()
        kwargs = {
            "config__module__codename": MobileModule.PRE_ENROLLMENT,
            "start_datetime": now - timedelta(days=7),
            "end_datetime": now + timedelta(hours=1),
        }
        handled = enrollment_schedule_factory(**kwargs)
        handled.events.create(event=events.PRE_ENROLLMENT_ENDED)
        pending = enrollment_schedule_factory(**kwargs)

        with mock.patch.object(
            services.tasks.pre_enrollment_end, "apply_async"
        ) as apply_async:
            services.enrollment_ending_schedule_watch()

        apply_async.assert_called_once_with((pending.id,), eta=pending.end_datetime)

    def test_upcoming_reminders(self, enrollment_schedule_factory):
        handled = enrollment_schedule_factory()
        for days in (1, 7):
            handled.events.create(
                event=events.ENROLLMENT_REMINDER_SENT,
                tag=timedelta(days=days).total_seconds(),
            )
        pending = enrollment_schedule_factory()

        with mock.patch.object(
            services.tasks.enrollment_reminder_send, "apply_async"
        ) as apply_async:
            services.enrollment_upcoming_schedule_watch()

        assert apply_async.call_count == 2
        assert {call.args[0] for call in apply_async.call_args_list} == {(pending.id,)}
        assert pending.events.count() == 2
