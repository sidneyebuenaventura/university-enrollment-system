import argparse
import csv
import sys

from django.core.management.base import BaseCommand

from university.core.cms.models import Classification
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
            sys.stdout.write(f"Classification data upload... ")

            created_counter = 0
            updated_counter = 0

            for row in reader:
                load_screen.spinner(spinner)

                _, created = Classification.objects.update_or_create(
                    ref_id=row.get("RUC"),
                    defaults={"name": row.get("RM_CLASS")},
                )
                if created:
                    created_counter += 1
                else:
                    updated_counter += 1

            message = f"\nSUCCESSFULLY PROCESSED {created_counter + updated_counter} CLASSIFICATION DATA."
            load_screen.print_statement(message, None)
            load_screen.print_statement(
                f"Created: {created_counter} records.", "created"
            )
            load_screen.print_statement(
                f"Updated: {updated_counter} records.\n", "updated"
            )
