from datetime import timedelta

from django.utils import timezone

from university.core import events
from university.core.accounts.constants import MobileModule, ReservedRole
from university.core.accounts.models import Role
from university.core.maintenance.models import EnrollmentSchedule

from . import tasks
from .selectors import enrollment_schedule_students_get


def _schedule_users(*, schedule: EnrollmentSchedule):
    return [
        student.user for student in enrollment_schedule_students_get(schedule=schedule)
    ]


def _schedule_role_add(*, schedule: EnrollmentSchedule, role_key: str):
    role = Role.objects.filter(name=role_key).first()

    if role:
        role.user_set.add(*_schedule_users(schedule=schedule))


def _schedule_role_remove(*, schedule: EnrollmentSchedule, role_key: str):
    role = Role.objects.filter(name=role_key).first()

    if role:
        role.user_set.remove(*_schedule_users(schedule=schedule))


# Blocked students still get access here. Holds for failed subjects or
# unpaid balances are applied by enrollment_status_evaluate.
def pre_enrollment_start(*, schedule: EnrollmentSchedule):
    _schedule_role_add(schedule=schedule, role_key=ReservedRole.STUDENT_PRE_ENROLLMENT)


def pre_enrollment_end(*, schedule: EnrollmentSchedule):
    _schedule_role_remove(
        schedule=schedule, role_key=ReservedRole.STUDENT_PRE_ENROLLMENT
    )


def enrollment_start(*, schedule: EnrollmentSchedule):
    _schedule_role_add(schedule=schedule, role_key=ReservedRole.STUDENT_ENROLLMENT)


def enrollment_end(*, schedule: EnrollmentSchedule):
    _schedule_role_remove(schedule=schedule, role_key=ReservedRole.STUDENT_ENROLLMENT)


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
