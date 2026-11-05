from unittest import mock

import pytest
from django.core import mail
from django.core.mail.backends.locmem import EmailBackend

from university.notification import tasks
from university.notification.messages import EMAIL_MESSAGES
from university.notification.models import EmailChannel, Notification


@pytest.fixture(autouse=True)
def locmem_backend():
    with mock.patch.object(tasks, "EmailBackend", EmailBackend):
        yield


@pytest.fixture(autouse=True)
def static_storage(settings):
    # The manifest storage needs collectstatic, which tests don't run
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }


def send(notification, **channel_kwargs):
    channel = EmailChannel.objects.create(**channel_kwargs)
    tasks.email_send(channel.id, notification.id)


@pytest.mark.django_db
@pytest.mark.parametrize("message_key", EMAIL_MESSAGES)
def test_every_message_renders(message_key, user):
    notification = Notification.objects.create(
        message_key=message_key,
        context={"full_name": "Juan dela Cruz", "enrollment_start": "June 1, 2026"},
    )
    notification.recipients.add(user)

    send(notification)

    sent = mail.outbox[-1]
    assert sent.to == [user.email]
    assert sent.subject == EMAIL_MESSAGES[message_key].subject
    assert sent.content_subtype == "html"
    # Reminders go to everyone, so they show the date instead of a name
    assert "Juan dela Cruz" in sent.body or "June 1, 2026" in sent.body


@pytest.mark.django_db
def test_whitelist(user_factory):
    allowed = user_factory(email="student@university.test")
    blocked = user_factory(email="someone@gmail.test")
    notification = Notification.objects.create(
        message_key=next(iter(EMAIL_MESSAGES)), context={}
    )
    notification.recipients.add(allowed, blocked)

    with mock.patch.object(tasks.settings, "EMAIL_WHITELIST", ["@university.test"]):
        send(notification, enable_whitelist=True)

    assert [message.to for message in mail.outbox] == [[allowed.email]]


@pytest.mark.django_db
def test_unknown_message_key_is_skipped(user):
    notification = Notification.objects.create(message_key="unknown")
    notification.recipients.add(user)

    send(notification)

    assert mail.outbox == []
