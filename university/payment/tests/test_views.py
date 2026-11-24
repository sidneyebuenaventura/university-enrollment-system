import pytest
from django.urls import reverse

from university.payment.models import PaymentMethods


@pytest.mark.django_db
def test_payment_methods(student_api_client):
    response = student_api_client.get(
        reverse("university.payment:payment-methods-list")
    )

    assert response.status_code == 200
    assert response.json() == [
        {"value": PaymentMethods.OTC.value, "label": PaymentMethods.OTC.label},
        {"value": PaymentMethods.CASHIER.value, "label": PaymentMethods.CASHIER.label},
    ]
