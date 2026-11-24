from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

import pytest
from django.contrib.auth.models import Group, Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework import exceptions

from university.payment import events, services
from university.payment.models import AccountTransaction, OverTheCounterTransaction
from university.payment.serializers import OverTheCounterCreateSerializer
from university.payment.tests.factories import StatementOfAccountFactory

Statuses = OverTheCounterTransaction.Statuses
Banks = OverTheCounterTransaction.Banks


@pytest.fixture
def publish():
    with mock.patch.object(services.event_publisher, "generic") as generic:
        yield generic


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def transfer(over_the_counter_transaction_factory, statement_of_account):
    transaction = over_the_counter_transaction_factory(
        soa=statement_of_account, bank=Banks.BDO
    )
    transaction.generate_id()
    return transaction


@pytest.fixture
def submitted(transfer):
    return services.otc_transaction_submit(
        transaction=transfer,
        transfer_reference="FT-12345",
        transfer_date=date.today(),
        amount=Decimal("5000.00"),
        receipt=receipt_file(),
    )


def receipt_file(name="receipt.png", content_type="image/png"):
    return SimpleUploadedFile(name, b"receipt", content_type=content_type)


def grant(user, *codenames):
    # Permissions only come from roles here, not from the user directly
    role = Group.objects.create(name="Finance")
    role.permissions.add(*Permission.objects.filter(codename__in=codenames))
    user.groups.add(role)


@pytest.mark.django_db
class TestFundTransferServices:
    def test_reference_comes_with_account_details(
        self, settings, statement_of_account, publish
    ):
        settings.UNIVERSITY_PAYMENT_BANK_ACCOUNTS = {"BDO": "0012-3456-7890"}

        with mock.patch.object(
            services.tasks.async_payment_transaction_expire, "apply_async"
        ):
            result = services.otc_transaction_create(
                soa=statement_of_account, data={"bank": Banks.BDO}
            )

        assert result["account_number"] == "0012-3456-7890"
        assert result["account_name"] == settings.UNIVERSITY_PAYMENT_BANK_ACCOUNT_NAME
        assert result["validation_days"] == 2

    def test_banks_without_an_account_are_refused(self, settings):
        settings.UNIVERSITY_PAYMENT_BANK_ACCOUNTS = {"BDO": "0012-3456-7890"}

        serializer = OverTheCounterCreateSerializer(
            data={"payment_method": "OTC", "bank": Banks.LBP}
        )

        assert not serializer.is_valid()
        assert "bank" in serializer.errors

    def test_submit(self, submitted):
        submitted.refresh_from_db()

        assert submitted.status == Statuses.FOR_VALIDATION
        assert submitted.amount == Decimal("5000.00")
        assert submitted.transfer_reference == "FT-12345"
        assert submitted.receipt
        assert submitted.validation_due == submitted.submitted_at + timedelta(days=2)

    def test_cannot_submit_twice(self, submitted):
        with pytest.raises(exceptions.ValidationError):
            services.otc_transaction_submit(
                transaction=submitted,
                transfer_reference="FT-99999",
                transfer_date=date.today(),
                amount=Decimal("100.00"),
                receipt=receipt_file(),
            )

    def test_submitted_transfer_does_not_expire(self, submitted):
        services.payment_transaction_expire(transaction=submitted)

        submitted.refresh_from_db()
        assert submitted.status == Statuses.FOR_VALIDATION

    def test_validate_credits_the_payment(self, submitted, staff_user, publish):
        services.otc_transaction_validate(transaction=submitted, staff=staff_user)

        submitted.refresh_from_db()
        credit = AccountTransaction.objects.get(ref_id=submitted.id)
        assert submitted.status == Statuses.SETTLED
        assert submitted.validated_by == staff_user
        assert credit.soa == submitted.soa
        assert credit.amount == Decimal("-5000.00")
        assert [call.args[0] for call in publish.call_args_list] == [
            events.PAYMENT_SUCCESS,
            events.PAYMENT_SETTLED,
        ]

    def test_validate_with_the_amount_that_arrived(
        self, submitted, staff_user, publish
    ):
        services.otc_transaction_validate(
            transaction=submitted, staff=staff_user, amount=Decimal("4500.00")
        )

        credit = AccountTransaction.objects.get(ref_id=submitted.id)
        assert credit.amount == Decimal("-4500.00")

    def test_only_submitted_transfers_can_be_validated(self, transfer, staff_user):
        with pytest.raises(exceptions.ValidationError):
            services.otc_transaction_validate(transaction=transfer, staff=staff_user)

    def test_reject(self, submitted, staff_user, publish):
        services.otc_transaction_reject(
            transaction=submitted, staff=staff_user, remarks="Amount not found"
        )

        submitted.refresh_from_db()
        assert submitted.status == Statuses.REJECTED
        assert submitted.remarks == "Amount not found"
        assert not AccountTransaction.objects.filter(ref_id=submitted.id).exists()
        publish.assert_called_once_with(events.PAYMENT_REJECTED, object=submitted)

    def test_overdue_after_the_lead_time(self, submitted):
        assert not submitted.is_overdue

        submitted.submitted_at = timezone.now() - timedelta(days=3)

        assert submitted.is_overdue

    def test_bank_file_settles_the_submitted_transfer(self, submitted, publish):
        services._journal_voucher_bank_process(
            student=submitted.soa.user.student,
            amount=Decimal("5000.00"),
            description="BDO transfer",
            jv_number="JV-1",
            bank=Banks.BDO,
        )

        submitted.refresh_from_db()
        assert submitted.status == Statuses.SETTLED
        assert OverTheCounterTransaction.objects.count() == 1


@pytest.mark.django_db
class TestStudentSubmit:
    def url(self, transaction):
        return reverse(
            "university.payment:student-otc-transactions-submit",
            args=[transaction.payment_id],
        )

    def data(self, **overrides):
        return {
            "transfer_reference": "FT-12345",
            "transfer_date": date.today().isoformat(),
            "amount": "5000.00",
            "receipt": receipt_file(),
            **overrides,
        }

    def test_submit(self, student_api_client, transfer):
        response = student_api_client.post(
            self.url(transfer), self.data(), format="multipart"
        )

        assert response.status_code == 200
        assert response.json()["status"] == Statuses.FOR_VALIDATION
        assert response.json()["validation_due"]

    def test_receipt_has_to_be_an_image_or_pdf(self, student_api_client, transfer):
        data = self.data(
            receipt=receipt_file("receipt.exe", "application/x-msdownload")
        )

        response = student_api_client.post(self.url(transfer), data, format="multipart")

        assert response.status_code == 400
        assert "receipt" in response.json()

    def test_transfer_date_cannot_be_in_the_future(self, student_api_client, transfer):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()

        response = student_api_client.post(
            self.url(transfer), self.data(transfer_date=tomorrow), format="multipart"
        )

        assert response.status_code == 400

    def test_cannot_submit_for_another_student(
        self, student_api_client, over_the_counter_transaction_factory
    ):
        other = over_the_counter_transaction_factory(soa=StatementOfAccountFactory())
        other.generate_id()

        response = student_api_client.post(
            self.url(other), self.data(), format="multipart"
        )

        assert response.status_code == 404


@pytest.mark.django_db
class TestFinanceValidation:
    def test_needs_permission(self, staff_api_client, submitted):
        url = reverse(
            "university.payment:otc-transactions-validate",
            args=[submitted.payment_id],
        )

        response = staff_api_client.post(url)

        assert response.status_code == 403

    def test_validate(self, staff_api_client, staff_user, submitted, publish):
        grant(staff_user, "change_overthecountertransaction")
        url = reverse(
            "university.payment:otc-transactions-validate",
            args=[submitted.payment_id],
        )

        response = staff_api_client.post(url)

        assert response.status_code == 200
        assert response.json()["status"] == Statuses.SETTLED

    def test_reject_needs_remarks(self, staff_api_client, staff_user, submitted):
        grant(staff_user, "change_overthecountertransaction")
        url = reverse(
            "university.payment:otc-transactions-reject", args=[submitted.payment_id]
        )

        response = staff_api_client.post(url, {})

        assert response.status_code == 400

    def test_reject(self, staff_api_client, staff_user, submitted, publish):
        grant(staff_user, "change_overthecountertransaction")
        url = reverse(
            "university.payment:otc-transactions-reject", args=[submitted.payment_id]
        )

        response = staff_api_client.post(url, {"remarks": "Amount not found"})

        assert response.status_code == 200
        assert response.json()["status"] == Statuses.REJECTED

    def test_list_overdue(
        self, staff_api_client, staff_user, submitted, over_the_counter_transaction
    ):
        grant(staff_user, "view_overthecountertransaction")
        OverTheCounterTransaction.objects.filter(id=submitted.id).update(
            submitted_at=timezone.now() - timedelta(days=3)
        )
        url = reverse("university.payment:otc-transactions-list")

        response = staff_api_client.get(url, {"overdue": "true"})

        results = response.json()["results"]
        assert response.status_code == 200
        assert [row["payment_id"] for row in results] == [submitted.payment_id]
        assert results[0]["is_overdue"]
