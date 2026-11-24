import pytest

from university.core.accounts.tests.factories import AcademicYearFactory


@pytest.mark.django_db
def test_schedule_school_year(enrollment_schedule_factory):
    schedule = enrollment_schedule_factory(
        academic_year=AcademicYearFactory(year_start=2025)
    )

    assert schedule.school_year == "2025-2026"
    assert "2025-2026" in str(schedule)


@pytest.mark.django_db
def test_schedule_without_academic_year(enrollment_schedule_factory):
    schedule = enrollment_schedule_factory()

    assert schedule.school_year == ""
    assert str(schedule)
