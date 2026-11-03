from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from kombu import Connection

from university.core import services
from university.framework.events import EventConsumer


class Command(BaseCommand):
    help = "Run core service consumer"

    def handle(self, *args, **options):
        self.stdout.write(f"[{timezone.now()}] - core service consumer starting")

        with Connection(settings.EVENT_BROKER_URL) as conn:
            consumer = EventConsumer(
                service_name="core", services=services, connection=conn
            )
            consumer.run()
