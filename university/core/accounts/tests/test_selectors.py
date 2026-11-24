from datetime import date, timedelta

import pytest

from university.core.accounts import selectors
from university.core.accounts.models import AcademicYear, Semester


def days(n):
    return date.today() + timedelta(days=n)


def school_year(year_start, date_start, date_end):
    return AcademicYear.objects.create(
        year_start=year_start,
        year_end=year_start + 1,
        date_start=date_start,
        date_end=date_end,
    )


@pytest.mark.django_db
class TestCurrentAcademicYear:
    def test_today_within_a_school_year(self):
        year = date.today().year
        school_year(year - 1, days(-400), days(-100))
        current = school_year(year, days(-30), days(270))

        assert selectors.current_academic_year_get() == current

    def test_between_school_years(self):
        year = date.today().year
        previous = school_year(year - 1, days(-300), days(-10))
        school_year(year, days(10), days(300))

        assert selectors.current_academic_year_get() == previous


@pytest.mark.django_db
def test_current_and_next_semester():
    year = school_year(date.today().year, days(-60), days(260))
    terms = [
        (Semester.Terms.SUMMER, 3, days(200), days(260)),
        (Semester.Terms.SECOND_SEMESTER, 2, days(80), days(190)),
        (Semester.Terms.FIRST_SEMESTER, 1, days(-60), days(60)),
    ]
    for term, order, date_start, date_end in terms:
        Semester.objects.create(
            academic_year=year,
            term=term,
            order=order,
            date_start=date_start,
            date_end=date_end,
        )

    assert selectors.current_semester_get().term == Semester.Terms.FIRST_SEMESTER
    assert selectors.next_semester_get().term == Semester.Terms.SECOND_SEMESTER
