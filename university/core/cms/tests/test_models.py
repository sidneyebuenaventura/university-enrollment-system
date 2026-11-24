import pytest

from university.core.cms.models import LaboratoryFee


@pytest.mark.django_db
def test_laboratory_fee_str(subject, academic_year):
    fee = LaboratoryFee.objects.create(
        subject=subject, academic_year=academic_year, rate=1500
    )

    assert str(fee) == f"{subject} - {academic_year}"
