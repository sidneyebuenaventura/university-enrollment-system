from celery import shared_task

from university.core import events
from university.core.maintenance.models import EnrollmentSchedule
from university.framework.events import GenericEvent


@shared_task
def pre_enrollment_reminder_send(schedule_id: int):
    schedule = EnrollmentSchedule.objects.get(id=schedule_id)
    event = GenericEvent(events.PRE_ENROLLMENT_REMINDER_SENT, schedule)
    event.publish()


@shared_task
def pre_enrollment_start(schedule_id: int):
    from .services import pre_enrollment_start as _pre_enrollment_start

    schedule = EnrollmentSchedule.objects.get(id=schedule_id)
    _pre_enrollment_start(schedule=schedule)


@shared_task
def pre_enrollment_end(schedule_id: int):
    from .services import pre_enrollment_end as _pre_enrollment_end

    schedule = EnrollmentSchedule.objects.get(id=schedule_id)
    _pre_enrollment_end(schedule=schedule)


@shared_task
def enrollment_reminder_send(schedule_id: int):
    schedule = EnrollmentSchedule.objects.get(id=schedule_id)
    event = GenericEvent(events.ENROLLMENT_REMINDER_SENT, schedule)
    event.publish()


@shared_task
def enrollment_start(schedule_id: int):
    from .services import enrollment_start as _enrollment_start

    schedule = EnrollmentSchedule.objects.get(id=schedule_id)
    _enrollment_start(schedule=schedule)


@shared_task
def enrollment_end(schedule_id: int):
    from .services import enrollment_end as _enrollment_end

    schedule = EnrollmentSchedule.objects.get(id=schedule_id)
    _enrollment_end(schedule=schedule)


@shared_task
def enrollment_schedule_watch():
    from .services import (
        enrollment_ending_schedule_watch,
        enrollment_starting_schedule_watch,
        enrollment_upcoming_schedule_watch,
    )

    enrollment_upcoming_schedule_watch()
    enrollment_starting_schedule_watch()
    enrollment_ending_schedule_watch()
