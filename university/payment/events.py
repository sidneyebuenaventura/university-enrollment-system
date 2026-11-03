from university.framework.events import EventBus

# Event names should follow the <service_name>.<event_name> format
PAYMENT_SUCCESS = "payment.payment_success"
PAYMENT_SETTLED = "payment.payment_settled"

DRAGONPAY_SETTLEMENT_CREATED = "payment.dragonpay_settlement_created"
BUKAS_SETTLEMENT_CREATED = "payment.bukas_settlement_created"
OTC_SETTLEMENT_CREATED = "payment.otc_settlement_created"
CASHIER_SETTLEMENT_CREATED = "payment.cashier_settlement_created"

JOURNAL_VOUCHER_CREATED = "payment.journal_voucher_created"

bus = EventBus(service_name="payment")
