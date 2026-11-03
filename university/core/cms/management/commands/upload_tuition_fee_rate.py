import argparse
import csv
import sys

from django.core.management.base import BaseCommand

from university.core.accounts.models import AcademicYear
from university.core.cms.models import TuitionFeeCategory, TuitionFeeRate
from university.framework.utils import LoadScreen

load_screen = LoadScreen()

category_mapping = {
    "MSIT/MIT": TuitionFeeCategory.Categories.MSIT_MIT,
    "DOCTORATE": TuitionFeeCategory.Categories.DOCTORATE,
    "PRO": TuitionFeeCategory.Categories.PROFESSIONAL,
    "NURSING": TuitionFeeCategory.Categories.NURSING,
    "GRAD PROG (MASTERAL)": TuitionFeeCategory.Categories.GRAD_PROG_MASTERAL,
    "LLM (MASTERAL LAW)": TuitionFeeCategory.Categories.LLM_MASTERAL_LAW,
    "COMP SCI": TuitionFeeCategory.Categories.COMPUTER_SCIENCE,
    "LAW": TuitionFeeCategory.Categories.LAW,
    "NSTP": TuitionFeeCategory.Categories.NSTP,
    "MSIT": TuitionFeeCategory.Categories.MSIT,
    "GRAD PROG": TuitionFeeCategory.Categories.GRADUATE_PROGRAM,
    "NONPRO": TuitionFeeCategory.Categories.NONPRO,
}


class Command(BaseCommand):
    help = "Run Subject Grouping data upload functionality"

    def add_arguments(self, parser):
        parser.add_argument("csvfile", nargs="?", type=argparse.FileType("r"))

    def handle(self, *args, **options):
        with options["csvfile"] as csvfile:
            reader = csv.DictReader(csvfile)

            spinner = load_screen.spinning_cursor()
            sys.stdout.write(f"Tuition Fee Rate data upload... ")

            created_counter = 0
            updated_counter = 0
            invalid_counter = 0

            for row in reader:
                load_screen.spinner(spinner)

                tfc = None
                if row.get("TF_CD"):
                    category_value = row.get("TF_DESC")[
                        row.get("TF_DESC").rfind("-") + 1 :
                    ].strip()
                    category = category_mapping.get(category_value)

                    tfc, _ = TuitionFeeCategory.objects.update_or_create(
                        ref_id=row.get("TF_CD"),
                        year_level=row.get("YRLEVEL"),
                        defaults={
                            "category": category,
                        },
                    )

                if not tfc:
                    invalid_counter += 1

                academic_year, created = AcademicYear.objects.get_or_create(
                    year_start=int(row.get("SYRE")) - 1,
                    year_end=int(row.get("SYRE")),
                )

                _, created = TuitionFeeRate.objects.update_or_create(
                    tuition_fee_category=tfc,
                    academic_year=academic_year,
                    defaults={"rate": row.get("RATE")},
                )

                if created:
                    created_counter += 1
                else:
                    updated_counter += 1

            message = f"\nSUCCESSFULLY PROCESSED {created_counter+updated_counter+invalid_counter} TUITION FEE RATE DATA."
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
