import argparse
import csv
import sys

from django.core.management.base import BaseCommand

from university.core.cms.models import Curriculum, CurriculumPeriod, Semesters
from university.framework.utils import LoadScreen

load_screen = LoadScreen()

sem_mapping = {
    "1": Semesters.FIRST_SEMESTER,
    "2": Semesters.SECOND_SEMESTER,
    "3": Semesters.SUMMER,
}


class Command(BaseCommand):
    help = "Run curriculum data upload functionality"

    def add_arguments(self, parser):
        parser.add_argument("csvfile", nargs="?", type=argparse.FileType("r"))

    def handle(self, *args, **options):
        with options["csvfile"] as csvfile:
            reader = csv.DictReader(csvfile)

            spinner = load_screen.spinning_cursor()
            sys.stdout.write(f"Curriculum Period data upload... ")

            created_counter = 0
            invalid_counter = 0
            existing_counter = 0

            for row in reader:
                load_screen.spinner(spinner)

                curriculum = Curriculum.objects.filter(
                    ref_id=row.get("CURR_CD")
                ).first()

                if curriculum:
                    _, created = CurriculumPeriod.objects.get_or_create(
                        curriculum=curriculum,
                        semester=sem_mapping.get(str(row.get("SEM"))),
                        year_level=int(row.get("YEAR")),
                    )
                    if created:
                        created_counter += 1
                    else:
                        existing_counter += 1

                else:
                    print(f"Invalid Curriculum Code: {row.get('CURR_CD')}")
                    invalid_counter += 1

            message = f"\nSUCCESSFULLY PROCESSED {created_counter + invalid_counter + existing_counter} CURRICULUM PERIOD DATA."
            load_screen.print_statement(message, None)
            load_screen.print_statement(
                f"Created: {created_counter} records.", "created"
            )
            load_screen.print_statement(
                f"Existing: {existing_counter} records.", "updated"
            )
            load_screen.print_statement(
                f"Invalid: {invalid_counter} records.\n", "invalid"
            )
