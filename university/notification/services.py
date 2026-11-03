from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator as token_generator
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from university.core.accounts.constants import ReservedRole
from university.core.accounts.models import Role
from university.framework.events import GenericEvent, GenericModelEvent
from university.framework.utils import format_currency
from university.notification.messages import MessageKeys
from university.payment.models import PaymentMethods

from . import app_settings
from .models import EmailChannel, Notification, NotificationChannel
from .tasks import email_send

User = get_user_model()


def notification_send(*, notification: Notification):
    channels = NotificationChannel.objects.filter(is_active=True)

    for channel in channels:
        channel_handler = channel.get_handler()
        channel_handler(channel=channel, notification=notification)


def email_handler(*, channel: EmailChannel, notification: Notification):
    email_send.delay(channel.id, notification.id)


def handle_enrollment_reminder_sent(event: GenericEvent):
    try:
        schedule = event.object
    except Exception:
        return

    student_role = Role.objects.filter(name=ReservedRole.STUDENT).first()

    if not student_role:
        return

    student_users = student_role.user_set.all()

    notification = Notification.objects.create(
        message_key="enrollment_reminders",
        context={
            "enrollment_start": timezone.localtime(schedule.start_datetime).strftime(
                app_settings.FORMAT_DATETIME
            )
        },
    )
    notification.recipients.add(*list(student_users))
    notification_send(notification=notification)


def handle_pre_enrollment_reminder_sent(event: GenericEvent):
    try:
        schedule = event.object
    except Exception:
        return

    student_role = Role.objects.filter(name=ReservedRole.STUDENT).first()

    if not student_role:
        return

    student_users = student_role.user_set.all()

    notification = Notification.objects.create(
        message_key="pre_enrollment_reminder",
        context={
            "enrollment_start": timezone.localtime(schedule.start_datetime).strftime(
                app_settings.FORMAT_DATETIME
            )
        },
    )
    notification.recipients.add(*list(student_users))
    notification_send(notification=notification)


def handle_payment_settled(event: GenericModelEvent):
    transaction = event.object.get_from_db()

    if not transaction:
        return

    enrollment = transaction.soa.enrollment
    academic_year = enrollment.academic_year
    user = transaction.soa.user
    student = user.student

    payment_method = transaction.type

    if payment_method == PaymentMethods.DRAGONPAY.label:
        channel = transaction.channel.description
        payment_method = f"{payment_method} - {channel}"
    elif payment_method == PaymentMethods.OTC.label:
        payment_method = f"{payment_method} - {transaction.bank}"

    notification = Notification.objects.create(
        message_key=MessageKeys.STATEMENT_OF_ACCOUNT,
        context={
            "full_name": f"{student.first_name} {student.last_name}",
            "student_id": student.id_number,
            "semester": enrollment.semester.get_term_display(),
            "year": f"{academic_year.year_start}-{academic_year.year_end}",
            "total_classes": enrollment.enrolled_classes.count(),
            "total_paid": format_currency(transaction.amount),
            "payment_method": payment_method,
        },
    )
    notification.recipients.add(transaction.soa.user)
    notification_send(notification=notification)


def handle_student_password_generated(event: GenericModelEvent):
    student = event.object.get_from_db()

    notification = Notification.objects.create(
        message_key=MessageKeys.STUDENT_LOGIN_CREDENTIALS,
        context={
            "full_name": f"{student.first_name} {student.last_name}",
            "username": student.user.username,
            "password": event.data.get("password"),
        },
    )
    notification.recipients.add(student.user)
    notification_send(notification=notification)


def handle_user_password_reset(event: GenericModelEvent):
    user = event.object.get_from_db()
    profile = user.get_profile()

    portal_url = app_settings.MESSAGE_STUDENT_PORTAL_URL

    if user.type == User.Types.ADMIN:
        portal_url = app_settings.MESSAGE_ADMIN_PORTAL_URL

    notification = Notification.objects.create(
        message_key=MessageKeys.USER_PASSWORD_RESET,
        context={
            "full_name": f"{profile.first_name} {profile.last_name}",
            "uid": urlsafe_base64_encode(force_bytes(user.pk)),
            "token": token_generator.make_token(user),
            "portal_url": portal_url,
        },
    )
    notification.recipients.add(user)
    notification_send(notification=notification)


def handle_enrollment_enrolled(event: GenericModelEvent):
    enrollment = event.object.get_from_db()
    student = enrollment.student
    academic_year = enrollment.academic_year
    classes = []

    for enrolled_class in enrollment.enrolled_classes.all():
        subject = enrolled_class.klass.curriculum_subject.subject
        instructor = enrolled_class.klass.instructor
        faculty = "-"

        if instructor:
            faculty = f"{instructor.first_name} {instructor.last_name}"

        schedules = []

        for schedule in enrolled_class.klass.class_schedules.all():
            if not schedule.is_valid():
                continue

            room = schedule.room.number

            if schedule.room.building:
                room = f"{room} {schedule.room.building.name}"

            day = schedule.get_day_display()
            schedules.append(f"{day} {schedule.time_in} {schedule.time_out} {room}")

        classes.append(
            {
                "subject": f"{subject.course_code}: {subject.descriptive_title}",
                "units": str(subject.units),
                "faculty": faculty,
                "schedules": schedules,
            }
        )

    notification = Notification.objects.create(
        message_key=MessageKeys.ENROLLMENT_SUCCESS,
        context={
            "full_name": f"{student.first_name} {student.last_name}",
            "semester": enrollment.semester.get_term_display(),
            "year": f"{academic_year.year_start}-{academic_year.year_end}",
            "classes": classes,
        },
    )
    notification.recipients.add(student.user)
    notification_send(notification=notification)


def handle_request_add_subject_approved(event: GenericModelEvent):
    request = event.object.get_from_db()

    notification = Notification.objects.create(
        message_key=MessageKeys.REQUEST_ADD_SUBJECT_APPROVED,
        context={
            "full_name": f"{request.student.first_name} {request.student.last_name}",
        },
    )
    notification.recipients.add(request.student.user)
    notification_send(notification=notification)


def handle_request_add_subject_rejected(event: GenericModelEvent):
    request = event.object.get_from_db()

    notification = Notification.objects.create(
        message_key=MessageKeys.REQUEST_ADD_SUBJECT_REJECTED,
        context={
            "full_name": f"{request.student.first_name} {request.student.last_name}",
            "remarks": event.data.get("remarks"),
        },
    )
    notification.recipients.add(request.student.user)
    notification_send(notification=notification)


def handle_request_change_schedule_approved(event: GenericModelEvent):
    request = event.object.get_from_db()

    notification = Notification.objects.create(
        message_key=MessageKeys.REQUEST_CHANGE_SCHEDULE_APPROVED,
        context={
            "full_name": f"{request.student.first_name} {request.student.last_name}",
        },
    )
    notification.recipients.add(request.student.user)
    notification_send(notification=notification)


def handle_request_change_schedule_rejected(event: GenericModelEvent):
    request = event.object.get_from_db()

    notification = Notification.objects.create(
        message_key=MessageKeys.REQUEST_CHANGE_SCHEDULE_REJECTED,
        context={
            "full_name": f"{request.student.first_name} {request.student.last_name}",
            "remarks": event.data.get("remarks"),
        },
    )
    notification.recipients.add(request.student.user)
    notification_send(notification=notification)


def handle_request_open_class_approved(event: GenericModelEvent):
    request = event.object.get_from_db()

    notification = Notification.objects.create(
        message_key=MessageKeys.REQUEST_OPEN_CLASS_APPROVED,
        context={
            "full_name": f"{request.student.first_name} {request.student.last_name}",
        },
    )
    notification.recipients.add(request.student.user)
    notification_send(notification=notification)


def handle_request_open_class_rejected(event: GenericModelEvent):
    request = event.object.get_from_db()

    notification = Notification.objects.create(
        message_key=MessageKeys.REQUEST_OPEN_CLASS_REJECTED,
        context={
            "full_name": f"{request.student.first_name} {request.student.last_name}",
            "remarks": event.data.get("remarks"),
        },
    )
    notification.recipients.add(request.student.user)
    notification_send(notification=notification)


def handle_request_open_class_for_approval(event: GenericModelEvent):
    request = event.object.get_from_db()

    notification = Notification.objects.create(
        message_key=MessageKeys.REQUEST_OPEN_CLASS_FOR_APPROVAL,
        context={
            "full_name": f"{request.student.first_name} {request.student.last_name}",
            "remarks": event.data.get("remarks"),
        },
    )
    notification.recipients.add(request.student.user)
    notification_send(notification=notification)


def handle_request_open_class_review_updated(event: GenericModelEvent):
    request = event.object.get_from_db()

    notification = Notification.objects.create(
        message_key=MessageKeys.REQUEST_OPEN_CLASS_REVIEW_UPDATED,
        context={
            "full_name": f"{request.student.first_name} {request.student.last_name}",
            "remarks": event.data.get("remarks"),
        },
    )
    notification.recipients.add(request.student.user)
    notification_send(notification=notification)


def handle_request_withdrawal_approved(event: GenericModelEvent):
    request = event.object.get_from_db()

    notification = Notification.objects.create(
        message_key=MessageKeys.REQUEST_WITHDRAWAL_APPROVED,
        context={
            "full_name": f"{request.student.first_name} {request.student.last_name}",
            "remarks": event.data.get("remarks"),
            "request_type": event.data.get("request_type"),
            "request_description": event.data.get("request_description"),
        },
    )
    notification.recipients.add(request.student.user)
    notification_send(notification=notification)


def handle_request_withdrawal_rejected(event: GenericModelEvent):
    request = event.object.get_from_db()

    notification = Notification.objects.create(
        message_key=MessageKeys.REQUEST_WITHDRAWAL_REJECTED,
        context={
            "full_name": f"{request.student.first_name} {request.student.last_name}",
            "remarks": event.data.get("remarks"),
            "request_type": event.data.get("request_type"),
            "request_description": event.data.get("request_description"),
        },
    )
    notification.recipients.add(request.student.user)
    notification_send(notification=notification)


def handle_request_withdrawal_for_approval(event: GenericModelEvent):
    request = event.object.get_from_db()

    notification = Notification.objects.create(
        message_key=MessageKeys.REQUEST_WITHDRAWAL_FOR_APPROVAL,
        context={
            "full_name": f"{request.student.first_name} {request.student.last_name}",
            "remarks": event.data.get("remarks"),
            "request_type": event.data.get("request_type"),
            "request_description": event.data.get("request_description"),
            "status": event.data.get("status"),
            "prev_status": event.data.get("prev_status"),
        },
    )
    notification.recipients.add(request.student.user)
    notification_send(notification=notification)


def handle_request_withdrawal_review_updated(event: GenericModelEvent):
    request = event.object.get_from_db()

    notification = Notification.objects.create(
        message_key=MessageKeys.REQUEST_WITHDRAWAL_REVIEW_UPDATED,
        context={
            "full_name": f"{request.student.first_name} {request.student.last_name}",
            "remarks": event.data.get("remarks"),
            "request_type": event.data.get("request_type"),
            "status": event.data.get("status"),
        },
    )
    notification.recipients.add(request.student.user)
    notification_send(notification=notification)
