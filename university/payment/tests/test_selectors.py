from decimal import Decimal

import pytest
from rest_framework import exceptions

from university.core.accounts.tests.factories import AcademicYearFactory
from university.core.students.tests.factories import EnrollmentFactory, StudentFactory
from university.payment import selectors
from university.payment.models import (
    BukasTransaction,
    CashierTransaction,
    DragonpayTransaction,
    OverTheCounterTransaction,
)
from university.payment.tests.factories import StatementOfAccountFactory


@pytest.mark.django_db
class TestSoaPaymentTotals:
    def test_paid_amount_only_counts_successful_payments(
        self,
        statement_of_account,
        dragonpay_transaction_factory,
        cashier_transaction_factory,
    ):
        soa = statement_of_account
        dragonpay_transaction_factory(
            soa=soa,
            amount=Decimal("1000.00"),
            status=DragonpayTransaction.Statuses.SUCCESS,
        )
        dragonpay_transaction_factory(
            soa=soa,
            amount=Decimal("500.00"),
            status=DragonpayTransaction.Statuses.FAILED,
        )
        cashier_transaction_factory(
            soa=soa, amount=Decimal("250.00"), status=CashierTransaction.Statuses.PAID
        )
        cashier_transaction_factory(soa=soa, amount=Decimal("300.00"))

        assert selectors.soa_get_paid_amount(soa=soa) == Decimal("1250.00")

    def test_settled_amount_only_counts_settled_payments(
        self,
        statement_of_account,
        dragonpay_transaction_factory,
        cashier_transaction_factory,
        bukas_transaction_factory,
    ):
        soa = statement_of_account
        dragonpay_transaction_factory(
            soa=soa,
            amount=Decimal("1000.00"),
            status=DragonpayTransaction.Statuses.SETTLED,
        )
        dragonpay_transaction_factory(
            soa=soa,
            amount=Decimal("700.00"),
            status=DragonpayTransaction.Statuses.SUCCESS,
        )
        cashier_transaction_factory(
            soa=soa,
            amount=Decimal("400.00"),
            status=CashierTransaction.Statuses.SETTLED,
        )
        # Bukas transactions have no amount until the lender sends one
        bukas_transaction_factory(
            soa=soa, amount=None, status=BukasTransaction.Statuses.FOR_FUNDING
        )

        assert selectors.soa_get_settled_amount(soa=soa) == Decimal("1400.00")


@pytest.mark.django_db
class TestSoaBalance:
    def test_min_amount_due_is_reduced_by_payments(
        self, statement_of_account_factory, account_transaction_factory
    ):
        soa = statement_of_account_factory(
            total_amount=Decimal("10000.00"), min_amount=Decimal("3500.00")
        )
        account_transaction_factory(soa=soa, amount=Decimal("10000.00"))
        account_transaction_factory(soa=soa, amount=Decimal("-1000.00"))

        assert selectors.soa_get_min_amount_due(soa=soa) == Decimal("2500.00")

    def test_min_amount_due_is_never_negative(
        self, statement_of_account_factory, account_transaction_factory
    ):
        soa = statement_of_account_factory(
            total_amount=Decimal("10000.00"), min_amount=Decimal("3500.00")
        )
        account_transaction_factory(soa=soa, amount=Decimal("10000.00"))
        account_transaction_factory(soa=soa, amount=Decimal("-5000.00"))

        assert selectors.soa_get_min_amount_due(soa=soa) == Decimal(0)

    def test_remaining_balance(self, statement_of_account, account_transaction_factory):
        soa = statement_of_account
        account_transaction_factory(soa=soa, amount=Decimal("10000.00"))
        account_transaction_factory(soa=soa, amount=Decimal("-4000.00"))

        assert selectors.soa_get_remaining_balance(soa=soa) == Decimal("6000.00")
        assert selectors.soa_get_available_credits(soa=soa) == Decimal(0)

    def test_remaining_balance_updates_flag(
        self, statement_of_account, account_transaction_factory
    ):
        soa = statement_of_account
        account_transaction_factory(soa=soa, amount=Decimal("10000.00"))
        selectors.soa_get_remaining_balance(soa=soa)
        soa.refresh_from_db()
        assert soa.has_remaining_balance

        account_transaction_factory(soa=soa, amount=Decimal("-10000.00"))
        selectors.soa_get_remaining_balance(soa=soa)
        soa.refresh_from_db()
        assert not soa.has_remaining_balance

    def test_overpayment_becomes_credit(
        self, statement_of_account, account_transaction_factory
    ):
        soa = statement_of_account
        account_transaction_factory(soa=soa, amount=Decimal("10000.00"))
        account_transaction_factory(soa=soa, amount=Decimal("-10500.00"))

        assert selectors.soa_get_remaining_balance(soa=soa) == Decimal(0)
        assert selectors.soa_get_available_credits(soa=soa) == Decimal("500.00")


@pytest.mark.django_db
class TestSoaGetLatest:
    def test_returns_soa_of_latest_academic_year(self):
        student = StudentFactory()
        old = StatementOfAccountFactory(
            enrollment=EnrollmentFactory(
                student=student, academic_year=AcademicYearFactory(year_start=2024)
            )
        )
        latest = StatementOfAccountFactory(
            enrollment=EnrollmentFactory(
                student=student, academic_year=AcademicYearFactory(year_start=2025)
            )
        )

        soa = selectors.soa_get_latest(user=student.user)

        assert soa == latest
        assert soa != old

    def test_raises_when_student_has_no_soa(self, student):
        assert selectors.soa_get_latest(user=student.user) is None

        with pytest.raises(exceptions.NotFound):
            selectors.soa_get_latest(user=student.user, raise_exception=True)


@pytest.mark.django_db
class TestTransactionLookups:
    def test_get_from_hash(self, cashier_transaction):
        cashier_transaction.generate_id()

        transaction = selectors.transaction_get_from_hash(
            hashed_id=cashier_transaction.payment_id
        )

        assert transaction.pk == cashier_transaction.pk
        assert isinstance(transaction, CashierTransaction)

    def test_get_from_invalid_hash(self):
        assert selectors.transaction_get_from_hash(hashed_id="INVALID") is None

        with pytest.raises(exceptions.NotFound):
            selectors.transaction_get_from_hash(
                hashed_id="INVALID", raise_exception=True
            )

    def test_otc_pending_returns_latest_pending(
        self, statement_of_account, over_the_counter_transaction_factory
    ):
        soa = statement_of_account
        over_the_counter_transaction_factory(soa=soa)
        latest = over_the_counter_transaction_factory(soa=soa)
        over_the_counter_transaction_factory(
            soa=soa, status=OverTheCounterTransaction.Statuses.FAILED
        )

        assert selectors.otc_transaction_get_pending(soa=soa) == latest

    def test_cashier_pending_ignores_paid(
        self, statement_of_account, cashier_transaction_factory
    ):
        soa = statement_of_account
        cashier_transaction_factory(soa=soa, status=CashierTransaction.Statuses.PAID)

        assert selectors.cashier_transaction_get_pending(soa=soa) is None

    def test_cashier_get_by_payment_id(self, cashier_transaction):
        cashier_transaction.generate_id()

        assert (
            selectors.cashier_transaction_get(payment_id=cashier_transaction.payment_id)
            == cashier_transaction
        )

        with pytest.raises(exceptions.NotFound):
            selectors.cashier_transaction_get(payment_id="NOPE", raise_exception=True)
