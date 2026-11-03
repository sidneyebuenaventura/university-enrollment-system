import argparse
import csv
import sys

from django.core.management.base import BaseCommand

from university.core.accounts.models import Department, Personnel, School
from university.framework.utils import LoadScreen

load_screen = LoadScreen()


class Command(BaseCommand):
    help = "Run department data upload functionality"

    def add_arguments(self, parser):
        parser.add_argument("csvfile", nargs="?", type=argparse.FileType("r"))

    def handle(self, *args, **options):
        with options["csvfile"] as csvfile:
            reader = csv.DictReader(csvfile)

            spinner = load_screen.spinning_cursor()
            sys.stdout.write("Department data upload... ")

            created_counter = 0
            updated_counter = 0

            for row in reader:
                load_screen.spinner(spinner)

                school = None
                if row.get("COLLEGE"):
                    school = School.objects.filter(ref_id=row.get("COLLEGE")).first()

                main_department = None
                if row.get("MAINDEPT"):
                    main_department = Department.objects.filter(
                        ref_id=row.get("MAINDEPT")
                    ).first()

                department_head = None
                if row.get("DEPTHEAD_IDNO"):
                    department_head = Personnel.objects.filter(
                        ref_id=row.get("DEPTHEAD_IDNO")
                    ).first()

                _, created = Department.objects.update_or_create(
                    ref_id=row.get("DEPT_CD"),
                    defaults={
                        "school": school,
                        "main_department": main_department,
                        "code": row.get("DEPT"),
                        "name": row.get("DEPARTMENT"),
                        "division_group": row.get("DIV_GRP"),
                        "department_head": department_head,
                    },
                )

                if created:
                    created_counter += 1
                else:
                    updated_counter += 1

            message = f"\nSUCCESSFULLY PROCESSED {created_counter + updated_counter} DEPARTMENT DATA."
            load_screen.print_statement(message, None)
            load_screen.print_statement(
                f"Created: {created_counter} records.", "created"
            )
            load_screen.print_statement(
                f"Updated: {updated_counter} records.\n", "updated"
            )
