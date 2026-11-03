import argparse
import csv
import sys

from django.core.management.base import BaseCommand

from university.core.accounts.models import School
from university.core.cms.models import Building
from university.framework.utils import LoadScreen

load_screen = LoadScreen()


class Command(BaseCommand):
    help = "Run building data upload functionality"

    def add_arguments(self, parser):
        parser.add_argument("csvfile", nargs="?", type=argparse.FileType("r"))

    def handle(self, *args, **options):
        with options["csvfile"] as csvfile:
            reader = csv.DictReader(csvfile)

            spinner = load_screen.spinning_cursor()
            sys.stdout.write("Building data upload... ")

            created_counter = 0
            updated_counter = 0

            for row in reader:
                load_screen.spinner(spinner)

                school_codes = []
                if row.get("HOMEOF"):
                    school_codes = row.get("HOMEOF").split("/")

                building, created = Building.objects.update_or_create(
                    ref_id=row.get("BLDGCD"),
                    defaults={
                        "sub_code": row.get("BLDGCHCD"),
                        "no_of_floors": row.get("FLOORS")
                        if row.get("FLOORS")
                        else None,
                        "name": row.get("BLDGNM"),
                        "campus": row.get("CAMPUS"),
                        "notes": row.get("HOMEOF"),
                    },
                )

                if school_codes:
                    schools = School.objects.filter(code__in=school_codes)
                    building.schools.add(*schools)

                if created:
                    created_counter += 1
                else:
                    updated_counter += 1

            message = f"\nSUCCESSFULLY PROCESSED {created_counter + updated_counter} BUILDING DATA."
            load_screen.print_statement(message, None)
            load_screen.print_statement(
                f"Created: {created_counter} records.", "created"
            )
            load_screen.print_statement(
                f"Updated: {updated_counter} records.\n", "updated"
            )
