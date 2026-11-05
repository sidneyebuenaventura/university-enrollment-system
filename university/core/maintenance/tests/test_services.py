import pytest

from university.core.accounts.constants import ReservedRole
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
