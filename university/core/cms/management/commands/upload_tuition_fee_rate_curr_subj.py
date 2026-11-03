import argparse
import csv
import sys

from django.core.management.base import BaseCommand
from django.db import transaction

from university.core.cms.models import CurriculumSubject, TuitionFeeCategory
from university.framework.utils import LoadScreen

load_screen = LoadScreen()


class Command(BaseCommand):
    help = "Run course data upload functionality"
    updated_counter = 0
    invalid_counter = 0

    def add_arguments(self, parser):
        parser.add_argument("csvfile", nargs="?", type=argparse.FileType("r"))

    def process_chunk(self, chunk):
        for data in chunk:
            load_screen.spinner(self.spinner)

            if not data.get("TFRCD"):
                print(f"Invalid Tuition Fee Rate Code {data.get('TFRCD')}")
                self.invalid_counter += 1
                continue

            tfc_id = self.tf_category_map.get(data.get("TFRCD"))

            if not tfc_id:
                print(f"Invalid Tuition Fee Rate Code {data.get('TFRCD')}")
                self.invalid_counter += 1
                continue

            if not data.get("SUBJ_CD"):
                print(f"Invalid Subject Code {data.get('SUBJ_CD')}")
                self.invalid_counter += 1
                continue

            curriculum_subjects = CurriculumSubject.objects.filter(
                subject__ref_id=data.get("SUBJ_CD"),
                curriculum_period__year_level=data.get("YRLEVEL"),
            )
            curriculum_subjects.update(tuition_fee_category=tfc_id)
            self.updated_counter += curriculum_subjects.count()

    def handle(self, *args, **options):
        """This upload will just update the tuition fee category of curriculum subject."""
        with options["csvfile"] as csvfile:
            reader = csv.DictReader(csvfile)

            self.spinner = load_screen.spinning_cursor()
            sys.stdout.write("Curriculum Subject Tuition Fee Category data upload... ")

            fields = ["id", "ref_id"]
            tf_categories = TuitionFeeCategory.objects.only(*fields).values(*fields)
            self.tf_category_map = {tfc["ref_id"]: tfc["id"] for tfc in tf_categories}

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

            total = self.updated_counter + self.invalid_counter
            message = f"\nSUCCESSFULLY PROCESSED {total} CURRICULUM SUBJECT TUITION FEE CATEGORY DATA."
            load_screen.print_statement(message, None)
            load_screen.print_statement(
                f"Updated: {self.updated_counter} records.", "updated"
            )
            load_screen.print_statement(
                f"Invalid: {self.invalid_counter} records.\n", "invalid"
            )
