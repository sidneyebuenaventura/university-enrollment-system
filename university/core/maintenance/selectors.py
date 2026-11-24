from university.core.accounts.constants import ReservedRole
from university.core.students.models import Student

from .models import EnrollmentSchedule


def enrollment_schedule_students_get(*, schedule: EnrollmentSchedule):
    """Students covered by a schedule. Empty schedule fields match everyone."""
    students = Student.objects.filter(
        user__groups__name=ReservedRole.STUDENT,
        year_level=schedule.year_level,
    )

    if schedule.student_type:
        students = students.filter(status=schedule.student_type)

    if schedule.course:
        students = students.filter(course=schedule.course)

    if schedule.school:
        students = students.filter(course__school=schedule.school)

    return students.select_related("user").order_by("id")
