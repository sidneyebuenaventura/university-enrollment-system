from django.core.management.base import BaseCommand

from university.core.accounts.models import AcademicYear, Semester


class Command(BaseCommand):
    help = "Creates Academic Year 2021-2022 Set"

    values = [
        {
            "year_start": "2021",
            "year_end": "2022",
            "year_date_start": "2021-08-16",
            "year_date_end": "2022-07-25",
            "fs_date_start": "2021-08-16",
            "fs_date_end": "2021-12-21",
            "ss_date_start": "2022-01-17",
            "ss_date_end": "2022-05-25",
            "s_date_start": "2022-06-13",
            "s_date_end": "2022-07-25",
        },
        {
            "year_start": "2022",
            "year_end": "2023",
            "year_date_start": "2022-08-15",
            "year_date_end": "2023-07-26",
            "fs_date_start": "2022-08-15",
            "fs_date_end": "2022-12-17",
            "ss_date_start": "2023-01-16",
            "ss_date_end": "2023-05-24",
            "s_date_start": "2023-06-13",
            "s_date_end": "2023-07-25",
        },
    ]

    def add_arguments(self, parser):
        parser.add_argument("idx", type=int)

    def handle(self, *args, **options):
        dates = self.values[options["idx"]]
        academic_year, created = AcademicYear.objects.update_or_create(
            year_start=dates.get("year_start"),
            year_end=dates.get("year_end"),
            defaults={
                "date_start": dates.get("year_date_start"),
                "date_end": dates.get("year_date_end"),
            },
        )

        semesters = [
            {
                "term": Semester.Terms.FIRST_SEMESTER,
                "order": 1,
                "date_start": dates.get("fs_date_start"),
                "date_end": dates.get("fs_date_end"),
            },
            {
                "term": Semester.Terms.SECOND_SEMESTER,
                "order": 2,
                "date_start": dates.get("ss_date_start"),
                "date_end": dates.get("ss_date_end"),
            },
            {
                "term": Semester.Terms.SUMMER,
                "order": 3,
                "date_start": dates.get("s_date_start"),
                "date_end": dates.get("s_date_end"),
            },
        ]

        for sem in semesters:
            Semester.objects.update_or_create(
                academic_year=academic_year,
                term=sem.get("term"),
                defaults={
                    "order": sem.get("order"),
                    "date_start": sem.get("date_start"),
                    "date_end": sem.get("date_end"),
                },
            )
