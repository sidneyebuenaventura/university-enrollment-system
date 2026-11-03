import argparse
import csv
import sys

from django.core.management.base import BaseCommand

from university.core.cms.models import Course, Curriculum, Semesters
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

    def handle(curriculumself, *args, **options):
        with options["csvfile"] as csvfile:
            reader = csv.DictReader(csvfile)

            spinner = load_screen.spinning_cursor()
            sys.stdout.write(f"Curriculum data upload... ")

            created_counter = 0
            updated_counter = 0
            invalid_counter = 0

            for row in reader:
                load_screen.spinner(spinner)

                course = None
                if row.get("DEG_CD"):
                    course = Course.objects.filter(code=row.get("DEG_CD")).first()

                if not course:
                    invalid_counter += 1
                    continue

                curriculum, created = Curriculum.objects.update_or_create(
                    ref_id=row.get("CURR_CD"),
                    defaults={
                        "course": course,
                        "effective_start_year": int(row.get("EFFECT_TERM")[0:4]) - 1,
                        "effective_end_year": int(row.get("EFFECT_TERM")[0:4]),
                        "effective_semester": sem_mapping.get(
                            str(row.get("EFFECT_TERM")[4:])
                        ),
                        "is_current": row.get("CURENT") in ["Y"],
                    },
                )

                if created:
                    created_counter += 1
                else:
                    updated_counter += 1

            message = f"\nSUCCESSFULLY PROCESSED {created_counter+updated_counter+invalid_counter} CURRICULUM DATA."
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
