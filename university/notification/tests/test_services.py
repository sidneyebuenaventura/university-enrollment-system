from decimal import Decimal
from unittest import mock

import pytest

from university.core import events
from university.core.cms.tests.factories import ClassScheduleFactory
from university.core.students.tests.factories import EnrolledClassFactory
from university.framework.events import GenericModelEvent
from university.notification import app_settings, services
from university.notification.messages import MessageKeys
from university.notification.models import EmailChannel, Notification
from university.payment.events import PAYMENT_SETTLED


def last_notification():
    return Notification.objects.latest("id")


@pytest.fixture
def email_send():
    with mock.patch.object(services.email_send, "delay") as delay:
        yield delay


@pytest.mark.django_db
class TestNotificationSend:
    def test_sends_through_active_channels(self, email_send):
        channel = EmailChannel.objects.create()
        EmailChannel.objects.create(is_active=False)
        notification = Notification.objects.create(message_key="test")

        services.notification_send(notification=notification)

        email_send.assert_called_once_with(channel.id, notification.id)


@pytest.mark.django_db
class TestAccountNotifications:
    def test_student_password_generated(self, student):
        event = GenericModelEvent(
            events.STUDENT_PASSWORD_GENERATED, object=student, password="s3cret"
        )

        services.handle_student_password_generated(event=event)

        notification = last_notification()
        assert notification.message_key == MessageKeys.STUDENT_LOGIN_CREDENTIALS
        assert list(notification.recipients.all()) == [student.user]
        assert notification.context["username"] == student.user.username
        assert notification.context["password"] == "s3cret"

    def test_student_password_reset_links_to_student_portal(self, student):
        user = student.user

        services.handle_user_password_reset(
            event=GenericModelEvent(events.USER_PASSWORD_RESET, object=user)
        )

        context = last_notification().context
        assert context["portal_url"] == app_settings.MESSAGE_STUDENT_PORTAL_URL
        assert context["full_name"] == f"{student.first_name} {student.last_name}"
        assert context["uid"] and context["token"]

    def test_admin_password_reset_links_to_admin_portal(self, personnel):
        user = personnel.user

        services.handle_user_password_reset(
            event=GenericModelEvent(events.USER_PASSWORD_RESET, object=user)
        )

        context = last_notification().context
        assert context["portal_url"] == app_settings.MESSAGE_ADMIN_PORTAL_URL


@pytest.mark.django_db
class TestRequestNotifications:
    @pytest.mark.parametrize(
        "request_fixture, event_name",
        [
            ("add_subject_request", events.REQUEST_ADD_SUBJECT_APPROVED),
            ("add_subject_request", events.REQUEST_ADD_SUBJECT_REJECTED),
            ("change_schedule_request", events.REQUEST_CHANGE_SCHEDULE_APPROVED),
            ("change_schedule_request", events.REQUEST_CHANGE_SCHEDULE_REJECTED),
            ("open_class_request", events.REQUEST_OPEN_CLASS_FOR_APPROVAL),
            ("open_class_request", events.REQUEST_OPEN_CLASS_REVIEW_UPDATED),
            ("open_class_request", events.REQUEST_OPEN_CLASS_APPROVED),
            ("open_class_request", events.REQUEST_OPEN_CLASS_REJECTED),
            ("withdrawal_request", events.REQUEST_WITHDRAWAL_FOR_APPROVAL),
            ("withdrawal_request", events.REQUEST_WITHDRAWAL_REVIEW_UPDATED),
            ("withdrawal_request", events.REQUEST_WITHDRAWAL_APPROVED),
            ("withdrawal_request", events.REQUEST_WITHDRAWAL_REJECTED),
        ],
    )
    def test_notifies_student(self, request, request_fixture, event_name):
        student_request = request.getfixturevalue(request_fixture)
        event = GenericModelEvent(event_name, object=student_request, remarks="Noted")
        handler = getattr(services, f"handle_{event.name}")

        handler(event=event)

        notification = last_notification()
        assert notification.message_key == event.name
        assert list(notification.recipients.all()) == [student_request.student.user]
        assert notification.context.get("remarks", "Noted") == "Noted"


@pytest.mark.django_db
class TestPaymentSettled:
    def test_dragonpay(self, dragonpay_transaction_factory):
        transaction = dragonpay_transaction_factory(amount=Decimal("1500.00"))

        services.handle_payment_settled(
            event=GenericModelEvent(PAYMENT_SETTLED, object=transaction)
        )

        notification = last_notification()
        student = transaction.soa.user.student
        assert notification.message_key == MessageKeys.STATEMENT_OF_ACCOUNT
        assert list(notification.recipients.all()) == [transaction.soa.user]
        assert notification.context["student_id"] == student.id_number
        assert notification.context["payment_method"] == (
            f"Dragonpay - {transaction.channel.description}"
        )
        assert "1,500.00" in notification.context["total_paid"]

    def test_over_the_counter(self, over_the_counter_transaction_factory):
        transaction = over_the_counter_transaction_factory(amount=Decimal("500.00"))

        services.handle_payment_settled(
            event=GenericModelEvent(PAYMENT_SETTLED, object=transaction)
        )

        assert last_notification().context["payment_method"] == (
            f"Bank - {transaction.bank}"
        )


def test_every_handler_has_a_matching_event():
    # Handlers are looked up by event name, so a typo means it never runs
    published = [
        value
        for value in [*vars(events).values(), PAYMENT_SETTLED]
        if isinstance(value, str) and "." in value
    ]
    event_names = {value.split(".")[1] for value in published}

    handlers = {
        name.removeprefix("handle_")
        for name in vars(services)
        if name.startswith("handle_")
    }

    assert handlers <= event_names


@pytest.mark.django_db
def test_enrollment_enrolled_lists_classes(base_enrollment):
    enrolled_class = EnrolledClassFactory(enrollment=base_enrollment)
    klass = enrolled_class.klass
    ClassScheduleFactory(klass=klass)

    services.handle_enrollment_enrolled(
        event=GenericModelEvent(events.ENROLLMENT_ENROLLED, object=base_enrollment)
    )

    notification = last_notification()
    assert notification.message_key == MessageKeys.ENROLLMENT_SUCCESS
    assert list(notification.recipients.all()) == [base_enrollment.student.user]
    [listed] = notification.context["classes"]
    assert listed["subject"] == (
        f"{klass.subject.course_code}: {klass.subject.descriptive_title}"
    )
    assert listed["faculty"] == (
        f"{klass.instructor.first_name} {klass.instructor.last_name}"
    )
    assert len(listed["schedules"]) == 1
