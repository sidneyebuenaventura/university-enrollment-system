import argparse
import csv
import sys

from django.core.management.base import BaseCommand

from university.core.accounts.models import Department
from university.core.cms.models import RemarkCode
from university.framework.utils import LoadScreen

load_screen = LoadScreen()


class Command(BaseCommand):
    help = "Run Remark Code data upload functionality"

    def add_arguments(self, parser):
        parser.add_argument("csvfile", nargs="?", type=argparse.FileType("r"))

    def handle(self, *args, **options):
        with options["csvfile"] as csvfile:
            reader = csv.DictReader(csvfile)

            spinner = load_screen.spinning_cursor()
            sys.stdout.write(f"Remark Code data upload... ")

            created_counter = 0
            updated_counter = 0

            for row in reader:
                load_screen.spinner(spinner)

                department = Department.objects.filter(
                    ref_id=row.get("DEPT_CD")
                ).first()

                _, created = RemarkCode.objects.update_or_create(
                    ref_id=row.get("COMM_CD"),
                    defaults={
                        "description": row.get("COMM_DESC"),
                        "department": department,
                    },
                )
                if created:
                    created_counter += 1
                else:
                    updated_counter += 1

            message = f"\nSUCCESSFULLY PROCESSED {created_counter+updated_counter} REMARKCODE DATA."
            load_screen.print_statement(message, None)
            load_screen.print_statement(
                f"Created: {created_counter} records.", "created"
            )
            load_screen.print_statement(
                f"Updated: {updated_counter} records.\n", "updated"
            )
