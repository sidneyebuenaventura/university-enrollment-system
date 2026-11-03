import argparse
import csv
import sys

from django.core.management.base import BaseCommand
from university.core.accounts.models import Department
from university.core.cms.models import Discount, Fee
from university.framework.utils import LoadScreen

load_screen = LoadScreen()


type_mapping = {
    "normal": Discount.Types.NORMAL,
    "scholarship": Discount.Types.SCHOLARSHIP,
}

apply_to_categories_mapping = {
    "TF": [Discount.ApplyToCategories.TUITION_FEE],
    "TOF": [
        Discount.ApplyToCategories.TUITION_FEE,
        Discount.ApplyToCategories.MISCELLANEOUS_FEE,
        Discount.ApplyToCategories.OTHER_FEE,
    ],
    "TFNP": [Discount.ApplyToCategories.TUITION_FEE],
    "TFX": [Discount.ApplyToCategories.TUITION_FEE],
}


class Command(BaseCommand):
    help = "Run schedule data upload functionality"

    def add_arguments(self, parser):
        parser.add_argument("csvfile", nargs="?", type=argparse.FileType("r"))

    def handle(self, *args, **options):
        with options["csvfile"] as csvfile:
            reader = csv.DictReader(csvfile)

            spinner = load_screen.spinning_cursor()
            sys.stdout.write(f"Discount data upload... ")

            created_counter = 0
            updated_counter = 0

            for row in reader:
                load_screen.spinner(spinner)

                department = None
                if row.get("DEPT"):
                    department = Department.objects.filter(
                        ref_id=row.get("DEPT")
                    ).first()

                fee_list = [code.strip() for code in row.get("FEE CODE").split(",")]
                fees = Fee.objects.filter(
                    code__in=fee_list,
                    academic_year__year_start=2022,
                    academic_year__year_end=2023,
                )

                discount, created = Discount.objects.update_or_create(
                    ref_id=row.get("DISCD"),
                    defaults={
                        "type": type_mapping.get(row.get("DISC_TYPE")),
                        "apply_to": apply_to_categories_mapping.get(
                            row.get("APPLIEDTO")
                        )
                        or [],
                        "name": row.get("DISC_SDESC"),
                        "percentage": row.get("PERCENT") if row.get("PERCENT") else 0,
                        "remarks": row.get("DISC_REMARKS"),
                        "department": department,
                        "is_confirmed": row.get("CONFIRM") in ["Y"],
                        "category_rate_exemption": row.get("CATEGORY").split(","),
                    },
                )

                discount.fee_exemptions.clear()
                discount.fee_exemptions.add(*fees)
                discount.save()

                if created:
                    created_counter += 1
                else:
                    updated_counter += 1

            message = f"\nSUCCESSFULLY PROCESSED {created_counter+updated_counter} DISCOUNT DATA."
            load_screen.print_statement(message, None)
            load_screen.print_statement(
                f"Created: {created_counter} records", "created"
            )
            load_screen.print_statement(
                f"Updated: {updated_counter} records\n", "updated"
            )
