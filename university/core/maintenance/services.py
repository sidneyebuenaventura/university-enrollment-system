from datetime import timedelta

from django.utils import timezone

from university.core import events
from university.core.accounts.constants import MobileModule, ReservedRole
from university.core.accounts.models import Role
from university.core.maintenance.models import EnrollmentSchedule
from university.core.students.selectors import (
    student_has_remaining_balance_get,
    student_has_failed_subject_get,
)
from university.core.students.models import Student

from . import tasks


def pre_enrollment_start(*, schedule: EnrollmentSchedule):
    student_role = Role.objects.filter(name=ReservedRole.STUDENT).first()
    pre_enrollment_role = Role.objects.filter(
        name=ReservedRole.STUDENT_PRE_ENROLLMENT
    ).first()

    if not student_role:
        return

    student_users = student_role.user_set.filter(
        status=schedule.student_type,
        course=schedule.course,
        course__school=schedule.school,
        next_curriculum_period__year_level=schedule.year_level,
    )

    for user in student_users:
        has_failed_subject = student_has_failed_subject_get(student=user.student)
        has_remaining_balance = student_has_remaining_balance_get(user=user)
        if has_failed_subject and has_remaining_balance:
            user.enrollment_status = (
                Student.EnrollmentStatuses.BLOCKED_WITH_OUTSTANDING_AND_FAILED_GRADE
            )
        elif has_failed_subject:
            user.enrollment_status = (
                Student.EnrollmentStatuses.BLOCKED_WITH_FAILED_SUBJECT
            )
        elif has_remaining_balance:
            user.enrollment_status = (
                Student.EnrollmentStatuses.BLOCKED_WITH_OUTSTANDING_BALANCE
            )
        else:
            user.enrollment_status = Student.EnrollmentStatuses.ALLOWED

        user.save()
        user.groups.add(pre_enrollment_role)


def pre_enrollment_end(*, schedule: EnrollmentSchedule):
    student_role = Role.objects.filter(name=ReservedRole.STUDENT).first()
    pre_enrollment_role = Role.objects.filter(
        name=ReservedRole.STUDENT_PRE_ENROLLMENT
    ).first()

    if not student_role:
        return

    student_users = student_role.user_set.filter(
        status=schedule.student_type,
        course=schedule.course,
        course__school=schedule.school,
        next_curriculum_period__year_level=schedule.year_level,
    )

    for user in student_users:
        user.groups.remove(pre_enrollment_role)


def enrollment_start(*, schedule: EnrollmentSchedule):
    student_role = Role.objects.filter(name=ReservedRole.STUDENT).first()
    enrollment_role = Role.objects.filter(name=ReservedRole.STUDENT_ENROLLMENT).first()

    if not student_role:
        return

    student_users = student_role.user_set.filter(
        status=schedule.student_type,
        course=schedule.course,
        course__school=schedule.school,
        current_curriculum_period=schedule.year_level,
    )

    for user in student_users:
        user.groups.add(enrollment_role)


def enrollment_end(*, schedule: EnrollmentSchedule):
    student_role = Role.objects.filter(name=ReservedRole.STUDENT).first()
    enrollment_role = Role.objects.filter(name=ReservedRole.STUDENT_ENROLLMENT).first()

    if not student_role:
        return

    student_users = student_role.user_set.filter(
        status=schedule.student_type,
        course=schedule.course,
        course__school=schedule.school,
        current_curriculum_period=schedule.year_level,
    )

    for user in student_users:
        user.groups.remove(enrollment_role)


def enrollment_upcoming_schedule_watch():
    now = timezone.now()
    reminder_offsets = [timedelta(days=1), timedelta(days=7)]

    for reminder_offset in reminder_offsets:
        upcoming_schedules = EnrollmentSchedule.objects.filter(
            start_datetime__range=(now, now + reminder_offset)
        )

        for schedule in upcoming_schedules:
            event_data = {
                "tag": reminder_offset.total_seconds(),
            }
            module_configs = {
                MobileModule.PRE_ENROLLMENT: {
                    "event": events.PRE_ENROLLMENT_REMINDER_SENT,
                    "task": tasks.pre_enrollment_reminder_send,
                },
                MobileModule.ENROLLMENT: {
                    "event": events.ENROLLMENT_REMINDER_SENT,
                    "task": tasks.enrollment_reminder_send,
                },
            }
            module_config = module_configs.get(schedule.config.module.codename)

            if not module_config:
                continue

            event_data["event"] = module_config["event"]
            reminded = schedule.events.filter(**event_data).exists()

            if reminded:
                return

            eta = schedule.start_datetime - reminder_offset
            module_config["task"].apply_async((schedule.id,), eta=eta)
            schedule.events.create(**event_data)


def enrollment_starting_schedule_watch():
    now = timezone.now()
    watch_until = now + timedelta(hours=1, minutes=30)
    datetime_range = (now, watch_until)

    starting_enrollment_schedules = EnrollmentSchedule.objects.filter(
        start_datetime__range=datetime_range
    )

    for schedule in starting_enrollment_schedules:
        module_configs = {
            MobileModule.PRE_ENROLLMENT: {
                "event": events.PRE_ENROLLMENT_STARTED,
                "task": tasks.pre_enrollment_start,
            },
            MobileModule.ENROLLMENT: {
                "event": events.ENROLLMENT_STARTED,
                "task": tasks.enrollment_start,
            },
        }
        module_config = module_configs.get(schedule.config.module.codename)

        if not module_config:
            continue

        event_data = {"event": module_config["event"]}
        started = schedule.events.filter(**event_data).exists()

        if started:
            return

        module_config["task"].apply_async((schedule.id,), eta=schedule.start_datetime)
        schedule.events.create(**event_data)


def enrollment_ending_schedule_watch():
    now = timezone.now()
    watch_until = now + timedelta(hours=1, minutes=30)
    datetime_range = (now, watch_until)

    ending_enrollment_schedules = EnrollmentSchedule.objects.filter(
        end_datetime__range=datetime_range
    )

    for schedule in ending_enrollment_schedules:
        module_configs = {
            MobileModule.PRE_ENROLLMENT: {
                "event": events.PRE_ENROLLMENT_ENDED,
                "task": tasks.pre_enrollment_end,
            },
            MobileModule.ENROLLMENT: {
                "event": events.ENROLLMENT_ENDED,
                "task": tasks.enrollment_end,
            },
        }
        module_config = module_configs.get(schedule.config.module.codename)

        if not module_config:
            continue

        event_data = {"event": module_config["event"]}
        ended = schedule.events.filter(**event_data).exists()

        if ended:
            return

        module_config["task"].apply_async((schedule.id,), eta=schedule.end_datetime)
        schedule.events.create(**event_data)
