import argparse
import csv
import sys

from django.core.management.base import BaseCommand

from university.core.cms.models import OtherFeeSpecification, Fee
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
            sys.stdout.write(f"Other Fee Specification Fees data upload... \n")

            created_counter = 0
            already_existing_counter = 0
            invalid_counter = 0

            for row in reader:
                load_screen.spinner(spinner)

                fee_specification = OtherFeeSpecification.objects.filter(
                    code=row.get("OFCD"),
                    academic_year__year_start=int(row.get("SYRE")[0:4]) - 1,
                    academic_year__year_end=int(row.get("SYRE")[0:4]),
                ).first()

                if not fee_specification:
                    print(f"Invalid Other Fee Spec Code: {row.get('OFCD')}")
                    invalid_counter += 1
                    continue

                fee = Fee.objects.filter(
                    code=row.get("MO_CD"), academic_year=fee_specification.academic_year
                ).first()

                if not fee:
                    print(
                        f"Invalid Fee Code: {row.get('MO_CD')} for AY {fee_specification.academic_year}"
                    )
                    invalid_counter += 1
                    continue

                if fee in fee_specification.fees.all():
                    already_existing_counter += 1
                    continue

                fee_specification.fees.add(fee)
                fee_specification.save()
                created_counter += 1

            message = f"\nSUCCESSFULLY PROCESSED {created_counter + already_existing_counter + invalid_counter} OTHER FEE SPECIFICATION  FEES DATA."
            load_screen.print_statement(message, None)
            load_screen.print_statement(
                f"Created: {created_counter} records.", "created"
            )
            load_screen.print_statement(
                f"Already Existing: {already_existing_counter} records.", "updated"
            )
            load_screen.print_statement(
                f"Invalid: {invalid_counter} records.\n", "invalid"
            )
