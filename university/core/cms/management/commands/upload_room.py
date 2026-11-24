import argparse
import csv
import sys

from django.core.management.base import BaseCommand

from university.core.accounts.models import School
from university.core.cms.models import Building, Classification, Room
from university.framework.utils import LoadScreen

load_screen = LoadScreen()


class Command(BaseCommand):
    help = "Run course data upload functionality"

    def add_arguments(self, parser):
        parser.add_argument("csvfile", nargs="?", type=argparse.FileType("r"))

    def handle(self, *args, **options):
        with options["csvfile"] as csvfile:
            reader = csv.DictReader(csvfile)

            spinner = load_screen.spinning_cursor()
            sys.stdout.write("Room data upload... ")

            created_counter = 0
            updated_counter = 0

            for row in reader:
                load_screen.spinner(spinner)

                school = None
                if row.get("COL_CD"):
                    school = School.objects.filter(ref_id=row.get("COL_CD")).first()

                building = None
                if row.get("BLDGCD"):
                    building = Building.objects.filter(ref_id=row.get("BLDGCD")).first()

                classification = None
                if row.get("RUC"):
                    classification = Classification.objects.filter(
                        ref_id=row.get("RUC")
                    ).first()

                room, created = Room.objects.update_or_create(
                    number=row.get("ROOM"),
                    defaults={
                        "school": school,
                        "classification": classification,
                        "building": building,
                        "name": row.get("RM_DESC"),
                        "size": row.get("RMSIZE"),
                        "floor_no": row.get("FLRNO") if row.get("FLRNO") else None,
                        "wing": row.get("WING"),
                        "capacity": row.get("CAP") if row.get("CAP") else None,
                        "furniture": row.get("FURN"),
                        "is_active": row.get("RMSTATUS") in [1],
                        "is_lecture_room": row.get("LECROOM") in [1],
                    },
                )

                if created:
                    created_counter += 1
                else:
                    updated_counter += 1

            message = f"\nSUCCESSFULLY PROCESSED {created_counter + updated_counter} ROOM DATA."
            load_screen.print_statement(message, None)
            load_screen.print_statement(
                f"Created: {created_counter} records.", "created"
            )
            load_screen.print_statement(
                f"Updated: {updated_counter} records.\n", "updated"
            )
