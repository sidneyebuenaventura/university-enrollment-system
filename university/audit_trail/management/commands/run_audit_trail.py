from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from kombu import Connection

from university.audit_trail import services
from university.framework.events import EventConsumer


class Command(BaseCommand):
    help = "Run audit_trail service consumer"

    def handle(self, *args, **options):
        self.stdout.write(f"[{timezone.now()}] - audit_trail service consumer starting")

        with Connection(settings.EVENT_BROKER_URL) as conn:
            consumer = EventConsumer(
                service_name="audit_trail", services=services, connection=conn
            )
            consumer.run()
