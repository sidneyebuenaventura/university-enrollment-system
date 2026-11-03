import argparse
import csv
import sys

from django.core.management.base import BaseCommand
from university.core.accounts.models import Department
from university.core.cms.models import SubjectGrouping
from university.framework.utils import LoadScreen

load_screen = LoadScreen()


class Command(BaseCommand):
    help = "Run Subject Grouping data upload functionality"

    def add_arguments(self, parser):
        parser.add_argument("csvfile", nargs="?", type=argparse.FileType("r"))

    def handle(self, *args, **options):
        with options["csvfile"] as csvfile:
            reader = csv.DictReader(csvfile)

            spinner = load_screen.spinning_cursor()
            sys.stdout.write(f"Subject Grouping data upload... ")

            created_counter = 0
            updated_counter = 0

            for row in reader:
                load_screen.spinner(spinner)

                department = None
                if row.get("DEPT_CD"):
                    department = Department.objects.filter(
                        ref_id=row.get("DEPT_CD")
                    ).first()

                subject_group, created = SubjectGrouping.objects.update_or_create(
                    ref_id=row.get("GRP_CD"),
                    defaults={
                        "name": row.get("GRP_DESC"),
                        "group_course": row.get("GRP_CORS"),
                        "department": department,
                        "is_gen_ed": row.get("GEN_ED") in ["Y"],
                    },
                )

                if created:
                    created_counter += 1
                else:
                    updated_counter += 1

            message = f"\nSUCCESSFULLY PROCESSED {created_counter + updated_counter} SUBJECT GROUPING DATA."
            load_screen.print_statement(message, None)
            load_screen.print_statement(
                f"Created: {created_counter} records.", "created"
            )
            load_screen.print_statement(
                f"Updated: {updated_counter} records.\n", "updated"
            )
