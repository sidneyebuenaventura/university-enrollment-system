import base64
import json

import structlog
from django.db import transaction as db_transaction
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.views import View
from django.views.generic import TemplateView
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import APIView

from university.core.students.models import Student
from university.core.students.selectors import (
    enrollment_bukas_transaction_get,
    enrollment_get_active,
)
from university.framework.events import event_publisher
from university.framework.parsers import PlainTextParser
from university.payment import events

from .. import models, selectors, services
from ..permissions import IsBukasWebhook, IsDragonpayWebhook

log = structlog.get_logger(__name__)


class PaymentTransactionView(View):
    def get(self, request, *args, **kwargs):
        hashed_id = kwargs.get("id")
        transaction = selectors.transaction_get_from_hash(hashed_id=hashed_id)

        if not transaction or not isinstance(transaction, models.BukasTransaction):
            raise Http404

        try:
            response = services.bukas_payment_create(transaction=transaction)
        except APIException:
            raise Http404

        return HttpResponse(response)


class DragonpayReturnView(TemplateView):
    template_name = "payment/payment_subpayment.html"
    extra_context = {"payment_gateway": "Dragonpay"}

    def get(self, request, *args, **kwargs):
        self.process_data(data=request.GET)
        return super().get(request, *args, **kwargs)

    def process_data(self, data):
        log.info("dragonpay_return", data=data)

        with db_transaction.atomic():
            transaction = selectors.transaction_get_from_hash(
                hashed_id=data.get("txnid"), lock=True
            )

            if not transaction or not isinstance(
                transaction, models.DragonpayTransaction
            ):
                raise Http404

            if transaction.soa.payments.count() <= 1:
                self.template_name = "payment/payment_enrollment.html"

            status = services.dragonpay_transaction_update(
                transaction=transaction, data=data
            )

        if status == models.DragonpayTransaction.Statuses.SUCCESS:
            event_publisher.generic(events.PAYMENT_SUCCESS, object=transaction)


class DragonpayPostbackAPIView(APIView):
    """Dragonpay Postback"""

    permission_classes = [IsDragonpayWebhook]

    def post(self, request, *args, **kwargs):
        self.process_data(data=request.data)
        return Response()

    def process_data(self, data):
        log_data = {"qs": self.request.query_params, "data": data}
        log.info("dragonpay_postback", **log_data)

        with db_transaction.atomic():
            transaction = selectors.transaction_get_from_hash(
                hashed_id=data.get("txnid"), lock=True
            )

            if not transaction:
                log.error("dragonpay_postback_transaction_404", **log_data)
                return

            status = services.dragonpay_transaction_update(
                transaction=transaction, data=data
            )

        if status == models.DragonpayTransaction.Statuses.SUCCESS:
            event_publisher.generic(events.PAYMENT_SUCCESS, object=transaction)


class BukasRedirectView(View):
    """Bukas Redirect Url"""

    def get(self, request):
        return render(
            request, "payment/payment_enrollment.html", {"payment_gateway": "Bukas"}
        )


class BukasWebhookAPIView(APIView):
    """Bukas Webhook"""

    parser_classes = [PlainTextParser]
    permission_classes = [IsBukasWebhook]

    @db_transaction.atomic
    def post(self, request):
        request_data = json.loads(base64.b64decode(request.data))
        log_data = {"qs": self.request.query_params, "data": request_data}
        log.info("bukas_webhook", **log_data)

        student = Student.objects.get(id_number=request_data.get("student_id_number"))

        enrollment = enrollment_get_active(user=student.user)
        if enrollment:
            bukas_transaction = enrollment_bukas_transaction_get(
                soa=enrollment.statement_of_account
            )
            services.bukas_transaction_update(
                transaction=bukas_transaction, data=request_data
            )
        else:
            log.error("bukas_webhook_transaction_404", **log_data)

        return Response(request_data)
