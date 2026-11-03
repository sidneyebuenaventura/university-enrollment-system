import argparse
import csv
import sys

from django.core.management.base import BaseCommand

from university.core.accounts.models import AcademicYear
from university.core.cms.models import Subject, LaboratoryFee
from university.framework.utils import LoadScreen

load_screen = LoadScreen()


class Command(BaseCommand):
    help = "Run Laboratory Fee data upload functionality"

    def add_arguments(self, parser):
        parser.add_argument("csvfile", nargs="?", type=argparse.FileType("r"))

    def handle(self, *args, **options):
        with options["csvfile"] as csvfile:
            reader = csv.DictReader(csvfile)

            spinner = load_screen.spinning_cursor()
            sys.stdout.write(f"Laboratory Fee data upload... ")

            created_counter = 0
            invalid_counter = 0
            updated_counter = 0

            for row in reader:
                load_screen.spinner(spinner)

                year_start = int(row.get("SYEAR")[0:4])
                year_end = int(row.get("SYEAR")[5:])

                academic_year, _ = AcademicYear.objects.get_or_create(
                    year_start=year_start,
                    year_end=year_end,
                )

                subjects = Subject.objects.filter(
                    course_number=row.get("SUBJECT").strip()
                )

                for subject in subjects:
                    if not subject:
                        print(f"Invalid Subject: {row.get('SUBJECT')}")
                        invalid_counter += 1

                    _, created = LaboratoryFee.objects.update_or_create(
                        subject=subject,
                        academic_year=academic_year,
                        defaults={"rate": row.get("LAB RATE")},
                    )

                    if created:
                        created_counter += 1
                    else:
                        updated_counter += 1

            message = f"\nSUCCESSFULLY PROCESSED {created_counter} BUILDING DATA."
            load_screen.print_statement(message, None)
            load_screen.print_statement(
                f"Created: {created_counter} records.", "created"
            )
            load_screen.print_statement(
                f"Updated: {updated_counter} records.", "updated"
            )
            load_screen.print_statement(
                f"Invalid: {invalid_counter} records.\n", "invalid"
            )
