import argparse
import csv
import sys

from django.core.management.base import BaseCommand

from university.core.accounts.models import AcademicYear, School
from university.core.cms.models import MiscellaneousFeeSpecification, Semesters, Subject
from university.framework.utils import LoadScreen

load_screen = LoadScreen()

sem_mapping = {
    "1": Semesters.FIRST_SEMESTER,
    "2": Semesters.SECOND_SEMESTER,
    "3": Semesters.SUMMER,
}


class Command(BaseCommand):
    help = "Run building data upload functionality"
    created_counter = 0
    updated_counter = 0

    def add_arguments(self, parser):
        parser.add_argument("csvfile", nargs="?", type=argparse.FileType("r"))

    def handle(self, *args, **options):
        with options["csvfile"] as csvfile:
            reader = csv.DictReader(csvfile)

            spinner = load_screen.spinning_cursor()
            sys.stdout.write(f"Miscellaneous Fee Specification data upload... ")

            for row in reader:
                load_screen.spinner(spinner)

                school = None
                if row.get("DEG1D"):
                    school = School.objects.filter(ref_id=row.get("DEG1D")).first()

                subject = None
                if row.get("CHRGCD"):
                    subject = Subject.objects.filter(
                        charge_code=row.get("CHRGCD")
                    ).first()

                academic_year, created = AcademicYear.objects.get_or_create(
                    year_start=int(row.get("SYRE")[0:4]) - 1,
                    year_end=int(row.get("SYRE")[0:4]),
                )

                (
                    fee_spec,
                    created,
                ) = MiscellaneousFeeSpecification.objects.update_or_create(
                    code=row.get("MFCD"),
                    academic_year=academic_year,
                    defaults={
                        "school": school,
                        "subject": subject,
                        "semester_from": sem_mapping.get(str(row.get("SEMR1")))
                        or Semesters.FIRST_SEMESTER,
                        "semester_to": sem_mapping.get(str(row.get("SEMR2")))
                        or Semesters.SUMMER,
                        "total_unit_from": row.get("UNTR1") if row.get("UNTR1") else 0,
                        "total_unit_to": row.get("UNTR1") if row.get("UNTR2") else 0,
                        "year_level_from": row.get("YRR1") or 1,
                        "year_level_to": row.get("YRR2") or 5,
                        "description": row.get("MFDESC"),
                    },
                )

                fee_spec.fees.clear()

                if created:
                    self.created_counter += 1
                else:
                    self.updated_counter += 1

            message = f"\nSUCCESSFULLY PROCESSED {self.created_counter + self.updated_counter} MISCELLANEOUS FEE SPECIFICATION DATA."
            load_screen.print_statement(message, None)
            load_screen.print_statement(
                f"Created: {self.created_counter} records.", "created"
            )
            load_screen.print_statement(
                f"Updated: {self.updated_counter} records.\n", "updated"
            )
