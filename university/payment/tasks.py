from celery import shared_task

from .models import JournalVoucher, PaymentSettlement, PaymentTransaction


@shared_task
def async_payment_settlement_process(settlement_id: int):
    from .services import payment_settlement_process

    settlement = PaymentSettlement.objects.filter(
        id=settlement_id, status=PaymentSettlement.Statuses.PENDING
    ).first()

    if not settlement:
        return

    payment_settlement_process(payment_settlement=settlement)


@shared_task
def async_journal_voucher_process(jv_id: int):
    from .services import journal_voucher_process

    jv = JournalVoucher.objects.filter(
        id=jv_id, status=PaymentSettlement.Statuses.PENDING
    ).first()

    if not jv:
        return

    journal_voucher_process(journal_voucher=jv)


@shared_task
def async_payment_transaction_expire(transaction_id: int):
    from .services import payment_transaction_expire

    transaction = PaymentTransaction.objects.filter(id=transaction_id).first()

    if not transaction:
        return

    payment_transaction_expire(transaction=transaction)
