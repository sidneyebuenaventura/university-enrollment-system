from django.core.management.base import BaseCommand

from university.core.accounts.models import AcademicYear, Semester


class Command(BaseCommand):
    help = "Creates initial Academic Year Set"

    def add_arguments(self, parser):
        parser.add_argument("year_start", type=int)
        parser.add_argument("year_end", type=int)

    def handle(self, *args, **options):
        academic_year, created = AcademicYear.objects.update_or_create(
            year_start=options["year_start"],
            year_end=options["year_end"],
        )

        semesters = [
            {"term": Semester.Terms.FIRST_SEMESTER, "order": 1},
            {"term": Semester.Terms.SECOND_SEMESTER, "order": 2},
            {"term": Semester.Terms.SUMMER, "order": 3},
        ]

        for sem in semesters:
            Semester.objects.update_or_create(
                academic_year=academic_year,
                term=sem.get("term"),
                defaults={"order": sem.get("order")},
            )
