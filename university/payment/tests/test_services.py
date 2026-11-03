from decimal import Decimal
from unittest import mock

import pytest
from django.conf import settings
from rest_framework import exceptions

from university.core.cms.tests.factories import (
    FeeFactory,
    MiscellaneousFeeSpecificationFactory,
    OtherFeeSpecificationFactory,
)
from university.core.students.models import Enrollment
from university.payment import events, services
from university.payment.models import (
    BukasTransaction,
    CashierTransaction,
    DragonpayTransaction,
    OverTheCounterTransaction,
    PaymentMethods,
)


@pytest.fixture
def expire_task():
    with mock.patch.object(
        services.tasks.async_payment_transaction_expire, "apply_async"
    ) as apply_async:
        yield apply_async


@pytest.mark.django_db
class TestDragonpayTransactionCreate:
    @pytest.fixture
    def soa(self, statement_of_account, dragonpay_key_factory):
        statement_of_account.min_amount = Decimal("3500.00")
        statement_of_account.save()
        dragonpay_key_factory(school=statement_of_account.get_school())
        return statement_of_account

    @pytest.fixture(autouse=True)
    def create_payment(self):
        with mock.patch.object(
            services.dragonpay_client,
            "create_payment",
            return_value="https://gateway.test/pay",
        ) as create_payment:
            yield create_payment

    def test_creates_transaction(self, soa, dragonpay_channel, create_payment):
        result = services.dragonpay_transaction_create(
            soa=soa, data={"amount": "5000.00", "channel": dragonpay_channel}
        )

        assert result == {"redirect_url": "https://gateway.test/pay"}
        create_payment.assert_called_once()

        transaction = soa.payments.get()
        assert transaction.amount == Decimal("5000.00")
        assert transaction.status == DragonpayTransaction.Statuses.PENDING
        assert transaction.payment_id

        soa.enrollment.refresh_from_db()
        assert soa.enrollment.step == Enrollment.Steps.PAYMENT

    def test_adds_channel_fees(self, soa, dragonpay_channel_factory):
        channel = dragonpay_channel_factory(
            addon_fixed=Decimal("20.00"), addon_percentage=Decimal("2.00")
        )

        services.dragonpay_transaction_create(
            soa=soa, data={"amount": "3980.00", "channel": channel}
        )

        # The channel takes 2% of the total, so (3980 + 20) / 0.98 = 4081.63
        transaction = soa.payments.get()
        assert transaction.addon_fee == Decimal("20.00")
        assert transaction.channel_fee == Decimal("81.63")
        assert transaction.total_amount_paid == Decimal("4081.63")

    def test_rejects_amount_below_minimum_due(self, soa, dragonpay_channel):
        with pytest.raises(exceptions.ValidationError):
            services.dragonpay_transaction_create(
                soa=soa, data={"amount": "1000.00", "channel": dragonpay_channel}
            )

        assert not soa.payments.exists()

    def test_requires_a_gateway_key(self, statement_of_account, dragonpay_channel):
        with pytest.raises(exceptions.ValidationError):
            services.dragonpay_transaction_create(
                soa=statement_of_account,
                data={"amount": "5000.00", "channel": dragonpay_channel},
            )


@pytest.mark.django_db
def test_dragonpay_update_returns_status_only_when_changed(dragonpay_transaction):
    data = {"status": "S", "refno": "REF-001", "message": "Payment received"}

    status = services.dragonpay_transaction_update(
        transaction=dragonpay_transaction, data=data
    )

    assert status == DragonpayTransaction.Statuses.SUCCESS
    assert dragonpay_transaction.reference_number == "REF-001"
    assert dragonpay_transaction.meta == data
    assert (
        services.dragonpay_transaction_update(
            transaction=dragonpay_transaction, data=data
        )
        is None
    )


@pytest.mark.django_db
class TestBukasTransaction:
    def test_create_returns_payment_service_url(self, statement_of_account):
        result = services.bukas_transaction_create(soa=statement_of_account, data={})

        transaction = statement_of_account.payments.get()
        assert result == {
            "redirect_url": f"{settings.UNIVERSITY_PAYMENT_SERVICE}"
            f"/transactions/{transaction.payment_id}/"
        }

    def test_for_funding_publishes_payment_success(self, bukas_transaction):
        data = {
            "status": "For Funding",
            "transaction_id": "TXN-001",
            "reference_code": "BK-001",
            "amount": "15000.00",
        }

        with mock.patch.object(services.event_publisher, "generic") as publish:
            services.bukas_transaction_update(transaction=bukas_transaction, data=data)

        assert bukas_transaction.status == BukasTransaction.Statuses.FOR_FUNDING
        assert bukas_transaction.reference_code == "BK-001"
        publish.assert_called_once_with(
            events.PAYMENT_SUCCESS, object=bukas_transaction
        )

    def test_disbursed_does_not_publish(self, bukas_transaction):
        with mock.patch.object(services.event_publisher, "generic") as publish:
            services.bukas_transaction_update(
                transaction=bukas_transaction, data={"status": "Disbursed"}
            )

        assert bukas_transaction.status == BukasTransaction.Statuses.DISBURSED
        publish.assert_not_called()


@pytest.mark.django_db
class TestReferenceNumberPayments:
    def test_otc_reuses_pending_transaction(self, statement_of_account, expire_task):
        data = {"bank": OverTheCounterTransaction.Banks.BDO}

        first = services.otc_transaction_create(soa=statement_of_account, data=data)
        second = services.otc_transaction_create(soa=statement_of_account, data=data)

        assert first == second
        assert statement_of_account.payments.count() == 1
        expire_task.assert_called_once()

    def test_cashier_reuses_pending_transaction(
        self, statement_of_account, expire_task
    ):
        first = services.cashier_transaction_create(soa=statement_of_account, data={})
        second = services.cashier_transaction_create(soa=statement_of_account, data={})

        assert first == second
        assert first["reference_number"]
        assert statement_of_account.payments.count() == 1
        expire_task.assert_called_once()

    def test_expired_transaction_is_failed(self, over_the_counter_transaction):
        over_the_counter_transaction.generate_id()

        services.payment_transaction_expire(transaction=over_the_counter_transaction)

        over_the_counter_transaction.refresh_from_db()
        assert (
            over_the_counter_transaction.status
            == OverTheCounterTransaction.Statuses.FAILED
        )
        assert (
            over_the_counter_transaction.payment_id
            in over_the_counter_transaction.error_message
        )


@pytest.mark.django_db
class TestCashierTransaction:
    def test_tag_as_paid(self, cashier_transaction, staff_user):
        services.cashier_transaction_tag_as_paid(
            transaction=cashier_transaction,
            cashier=staff_user,
            amount=Decimal("1500.00"),
            receipt_id="OR-0001",
        )

        cashier_transaction.refresh_from_db()
        assert cashier_transaction.status == CashierTransaction.Statuses.PAID
        assert cashier_transaction.amount == Decimal("1500.00")
        assert cashier_transaction.receipt_id == "OR-0001"
        assert cashier_transaction.processed_by == staff_user
        assert cashier_transaction.processed_at

    def test_only_pending_can_be_tagged_as_paid(self, cashier_transaction_factory):
        transaction = cashier_transaction_factory(
            status=CashierTransaction.Statuses.VOIDED
        )

        with pytest.raises(exceptions.PermissionDenied):
            services.cashier_transaction_tag_as_paid(transaction=transaction)

    def test_void(self, cashier_transaction_factory):
        transaction = cashier_transaction_factory(
            status=CashierTransaction.Statuses.PAID
        )

        services.cashier_transaction_void(
            transaction=transaction, remarks="Wrong amount"
        )

        transaction.refresh_from_db()
        assert transaction.status == CashierTransaction.Statuses.VOIDED
        assert transaction.remarks == "Wrong amount"

    def test_pending_cannot_be_voided(self, cashier_transaction):
        with pytest.raises(exceptions.PermissionDenied):
            services.cashier_transaction_void(transaction=cashier_transaction)


@pytest.mark.django_db
class TestPaymentCreate:
    def test_uses_selected_payment_method(self, statement_of_account, expire_task):
        result = services.payment_create(
            user=statement_of_account.user,
            data={"payment_method": PaymentMethods.CASHIER},
        )

        transaction = statement_of_account.payments.get()
        assert isinstance(transaction, CashierTransaction)
        assert result == {"reference_number": transaction.payment_id}

    def test_student_without_soa(self, student):
        with pytest.raises(exceptions.NotFound):
            services.payment_create(
                user=student.user, data={"payment_method": PaymentMethods.CASHIER}
            )


@pytest.mark.django_db
class TestSoaCreate:
    @pytest.fixture
    def enrollment(self, base_enrollment):
        base_enrollment.miscellaneous_fee_specification = (
            MiscellaneousFeeSpecificationFactory(
                fees=[
                    FeeFactory(amount=Decimal("1000.00")),
                    FeeFactory(amount=Decimal("500.00")),
                ]
            )
        )
        base_enrollment.other_fee_specification = OtherFeeSpecificationFactory(
            fees=[FeeFactory(amount=Decimal("250.00"))]
        )
        base_enrollment.save()
        return base_enrollment

    def test_builds_statement_from_fees(self, enrollment):
        soa = services.soa_create(enrollment=enrollment)

        assert soa.user == enrollment.student.user
        assert soa.total_amount == Decimal("1750.00")
        assert soa.min_amount == Decimal("612.50")
        assert soa.lines.count() == 3
        assert soa.categories.count() == 2
        assert soa.get_remaining_balance() == Decimal("1750.00")

    def test_rebuilding_replaces_previous_lines(self, enrollment):
        services.soa_create(enrollment=enrollment)
        soa = services.soa_create(enrollment=enrollment, override=True)

        assert enrollment.student.user.statement_of_accounts.count() == 1
        assert soa.lines.count() == 3
        assert soa.transactions.count() == 2
