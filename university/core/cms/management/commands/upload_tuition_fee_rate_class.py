import argparse
import csv
import sys

from django.core.management.base import BaseCommand
from django.db import transaction
from university.core.accounts.models import AcademicYear

from university.core.cms.models import Class, TuitionFeeCategory, TuitionFeeRate
from university.framework.utils import LoadScreen

load_screen = LoadScreen()


class Command(BaseCommand):
    help = "Run course data upload functionality"
    updated_counter = 0
    invalid_counter = 0
    total_counter = 0

    def add_arguments(self, parser):
        parser.add_argument("csvfile", nargs="?", type=argparse.FileType("r"))

    def process_chunk(self, chunk):
        for data in chunk:
            self.total_counter += 1
            # load_screen.spinner(self.spinner)

            if not data.get("TFRCD"):
                print(f"Invalid Tuition Fee Rate Code {data.get('TFRCD')}")
                self.invalid_counter += 1
                continue
            academic_year = AcademicYear.objects.filter(
                year_end=int(data.get("SYRE"))
            ).first()

            if not academic_year:
                print(f"Invalid Academic Year {data.get('TFRCD')} | {data.get('SYRE')}")
                self.invalid_counter += 1
                continue

            tfc = TuitionFeeCategory.objects.filter(
                ref_id=data.get("TFRCD"), year_level=data.get("YRLEVEL")
            ).first()

            if not tfc:
                print(
                    f"Invalid TFRCode {data.get('TFRCD')} | Year level: {data.get('YRLEVEL')}"
                )
                self.invalid_counter += 1
                continue

            tfr = tfc.rates.filter(academic_year=academic_year).first()
            if not academic_year:
                print(
                    f"Invalid Tuition Fee Rate Code {data.get('TFRCD')} for Academic Year {data.get('SYRE')}"
                )
                self.invalid_counter += 1
                continue

            if not data.get("SUBJ_CD"):
                print(f"Invalid Subject Code {data.get('SUBJ_CD')}")
                self.invalid_counter += 1
                continue

            classes = Class.objects.filter(
                semester__academic_year=academic_year,
                subject__ref_id=data.get("SUBJ_CD"),
                year_level=data.get("YRLEVEL"),
            )

            print(
                f"TFNO: {data.get('TFNO')} | Academic Year: {data.get('SYRE')}  Class Count: {classes.count()}"
            )

            classes.update(tuition_fee_rate=tfr)
            self.updated_counter += classes.count()

    def handle(self, *args, **options):
        """This upload will just update the tuition fee rate of classes."""
        with options["csvfile"] as csvfile:
            reader = csv.DictReader(csvfile)

            self.spinner = load_screen.spinning_cursor()
            sys.stdout.write(f"Class Tuition Fee Rate data upload... \n")

            chunk = []
            chunk_size = 1000

            for index, row in enumerate(reader):
                chunk.append(row)

                if index % chunk_size != 0:
                    continue

                # By committing updates in a transaction, we only reach the db
                # once every `chunk_size`.
                with transaction.atomic():
                    self.process_chunk(chunk)

                # Reset chunk
                chunk = []

            # Process remaining chunk
            self.process_chunk(chunk)

            message = f"\nSUCCESSFULLY PROCESSED {self.total_counter} CURRICULUM SUBJECT TUITION FEE CATEGORY DATA."
            load_screen.print_statement(message, None)
            load_screen.print_statement(
                f"Updated: {self.updated_counter} records.", "updated"
            )
            load_screen.print_statement(
                f"Invalid: {self.invalid_counter} records.\n", "invalid"
            )
