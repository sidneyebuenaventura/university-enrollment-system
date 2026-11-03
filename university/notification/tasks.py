from dataclasses import asdict

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.core.mail.backends.smtp import EmailBackend
from django.template.loader import render_to_string

from . import app_settings
from .messages import EMAIL_MESSAGES
from .models import EmailChannel, Notification


def _in_email_whitelist(email):
    for rule in settings.EMAIL_WHITELIST:
        if rule.startswith("@"):
            if email.split("@")[1] == rule[1:]:
                return True
        elif email == rule:
            return True


@shared_task
def email_send(channel_id: int, notification_id: int):
    channel = EmailChannel.objects.get(id=channel_id)
    notification = Notification.objects.get(id=notification_id)

    with EmailBackend(
        host=channel.host,
        port=channel.port,
        username=channel.user,
        password=channel.password,
        use_tls=channel.use_tls,
        use_ssl=channel.use_ssl,
    ) as connection:
        email_message = EMAIL_MESSAGES.get(notification.message_key)

        if not email_message:
            return

        email_data = asdict(email_message)

        body = email_data.pop("body")
        template_name = email_data.pop("template")

        if template_name:
            context = {"notification": notification, "app_settings": app_settings}
            context.update(notification.context)
            body = render_to_string(template_name, context)

        for recipient in notification.recipients.all():
            if channel.enable_whitelist and not _in_email_whitelist(recipient.email):
                continue

            msg = EmailMessage(
                body=body,
                from_email=channel.default_from,
                to=[recipient.email],
                connection=connection,
                **email_data,
            )

            if template_name:
                msg.content_subtype = "html"

            msg.send()
