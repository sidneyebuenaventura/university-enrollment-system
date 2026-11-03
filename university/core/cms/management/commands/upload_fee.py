import argparse
import csv
import sys

from django.core.management.base import BaseCommand

from university.core.accounts.models import AcademicYear
from university.core.cms.models import Fee
from university.framework.utils import LoadScreen

load_screen = LoadScreen()


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
            sys.stdout.write(f"Fee data upload... ")

            Fee.objects.filter(academic_year__isnull=True).delete()

            for row in reader:
                load_screen.spinner(spinner)

                academic_year, created = AcademicYear.objects.get_or_create(
                    year_start=int(row.get("SYRE")[0:4]) - 1,
                    year_end=int(row.get("SYRE")[0:4]),
                )

                fee, created = Fee.objects.update_or_create(
                    code=row.get("MO_CD"),
                    academic_year=academic_year,
                    defaults={
                        "name": row.get("MO_DESC"),
                        "description": row.get("S_DESC"),
                        "type": row.get("M_O"),
                        "remarks": row.get("REMARKS"),
                        "amount": row.get("FEE") if row.get("FEE") else 0,
                        "is_active": row.get("MOSTATUS") not in ["I"],
                    },
                )

                if created:
                    self.created_counter += 1
                else:
                    self.updated_counter += 1

            message = f"\nSUCCESSFULLY PROCESSED {self.created_counter+self.updated_counter} FEE DATA."
            load_screen.print_statement(message, None)
            load_screen.print_statement(
                f"Created: {self.created_counter} records.", "created"
            )
            load_screen.print_statement(
                f"Updated: {self.updated_counter} records.\n", "updated"
            )
