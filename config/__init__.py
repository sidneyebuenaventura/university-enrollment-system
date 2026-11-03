# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celery import app as celery_app

# Make sure openapi extensions are always loaded
import university.core.openapi as core_openapi
import university.payment.openapi as payment_openapi

__all__ = ("celery_app", "core_openapi", "payment_openapi")
