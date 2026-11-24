from decimal import Decimal

import pytest
from django.urls import reverse

from university.payment.models import CashierTransaction, OverTheCounterTransaction
from university.payment.tests.factories import StatementOfAccountFactory

ENDPOINTS = [
    ("cashier_transaction_factory", "student-cashier-transactions-detail"),
    ("over_the_counter_transaction_factory", "student-otc-transactions-detail"),
]

PENDING = "P"
FAILED = "F"


def update_url(transaction, url_name):
    transaction.generate_id()
    return reverse(f"university.payment:{url_name}", args=[transaction.payment_id])


@pytest.mark.django_db
@pytest.mark.parametrize("factory, url_name", ENDPOINTS)
class TestStudentTransactionUpdate:
    def test_can_cancel_own_pending_reference(
        self, request, student_api_client, statement_of_account, factory, url_name
    ):
        transaction = request.getfixturevalue(factory)(soa=statement_of_account)

        response = student_api_client.patch(
            update_url(transaction, url_name), {"status": FAILED}
        )

        transaction.refresh_from_db()
        assert response.status_code == 200
        assert transaction.status == FAILED

    def test_cannot_mark_own_reference_as_paid(
        self, request, student_api_client, statement_of_account, factory, url_name
    ):
        transaction = request.getfixturevalue(factory)(soa=statement_of_account)

        response = student_api_client.patch(
            update_url(transaction, url_name), {"status": "S"}
        )

        transaction.refresh_from_db()
        assert response.status_code == 400
        assert transaction.status == PENDING

    def test_cannot_cancel_a_paid_transaction(
        self, request, student_api_client, statement_of_account, factory, url_name
    ):
        transaction = request.getfixturevalue(factory)(
            soa=statement_of_account, amount=Decimal("500.00"), status="S"
        )

        response = student_api_client.patch(
            update_url(transaction, url_name), {"status": FAILED}
        )

        transaction.refresh_from_db()
        assert response.status_code == 400
        assert transaction.status == "S"

    def test_cannot_touch_another_students_transaction(
        self, request, student_api_client, statement_of_account, factory, url_name
    ):
        other_soa = StatementOfAccountFactory()
        transaction = request.getfixturevalue(factory)(soa=other_soa)

        response = student_api_client.patch(
            update_url(transaction, url_name), {"status": FAILED}
        )

        transaction.refresh_from_db()
        assert response.status_code == 404
        assert transaction.status == PENDING


def test_status_codes_match_the_models():
    # The tests above use raw codes, so make sure they mean the same thing
    for model in (CashierTransaction, OverTheCounterTransaction):
        assert model.Statuses.PENDING == PENDING
        assert model.Statuses.FAILED == FAILED
    assert CashierTransaction.Statuses.PAID == "S"
    assert OverTheCounterTransaction.Statuses.SUCCESS == "S"
