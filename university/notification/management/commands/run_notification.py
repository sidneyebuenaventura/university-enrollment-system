from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from kombu import Connection

from university.framework.events import EventConsumer
from university.notification import services


class Command(BaseCommand):
    help = "Run notification service consumer"

    def handle(self, *args, **options):
        self.stdout.write(
            f"[{timezone.now()}] - notification service consumer starting"
        )

        with Connection(settings.EVENT_BROKER_URL) as conn:
            consumer = EventConsumer(
                service_name="notification", services=services, connection=conn
            )
            consumer.run()
