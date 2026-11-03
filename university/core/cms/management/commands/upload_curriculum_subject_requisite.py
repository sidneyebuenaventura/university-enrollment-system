import argparse
import csv
import sys

from django.core.management.base import BaseCommand

from university.core.cms.models import (
    Curriculum,
    CurriculumSubject,
    CurriculumSubjectRequisite,
)
from university.framework.utils import LoadScreen

load_screen = LoadScreen()


class Command(BaseCommand):
    help = "Run curriculum subject requisite data upload functionality"

    def add_arguments(self, parser):
        parser.add_argument("csvfile", nargs="?", type=argparse.FileType("r"))

    def handle(self, *args, **options):
        with options["csvfile"] as csvfile:
            reader = csv.DictReader(csvfile)

            spinner = load_screen.spinning_cursor()
            sys.stdout.write("Curriculum Subject Requisite data upload... ")

            created_counter = 0
            updated_counter = 0
            invalid_counter = 0

            for row in reader:
                load_screen.spinner(spinner)

                curriculum = None
                if row.get("CURR_CD"):
                    curriculum = Curriculum.objects.filter(
                        ref_id=row.get("CURR_CD")
                    ).first()

                if not curriculum:
                    invalid_counter += 1
                    continue

                # Get the CurriculumSubject object for main subject
                subject = CurriculumSubject.objects.filter(
                    curriculum_period__curriculum=curriculum,
                    subject__ref_id=row.get("SUBJ_CD"),
                ).first()

                if not subject:
                    invalid_counter += 1
                    continue

                # Get the CurriculumSubject object for requisite subject
                req_subject = CurriculumSubject.objects.filter(
                    curriculum_period__curriculum=curriculum,
                    subject__ref_id=row.get("PS_CD"),
                ).first()

                if not req_subject:
                    invalid_counter += 1
                    continue

                _, created = CurriculumSubjectRequisite.objects.update_or_create(
                    curriculum_subject=subject,
                    requisite_subject=req_subject,
                    defaults={
                        "type": CurriculumSubjectRequisite.Types.CO_REQUISITE
                        if row.get("SAME")
                        else CurriculumSubjectRequisite.Types.PRE_REQUISITE,
                    },
                )

                if created:
                    created_counter += 1
                else:
                    updated_counter += 1

            message = f"\nSUCCESSFULLY PROCESSED {created_counter + updated_counter} CURRICULUM SUBJECT REQUISITE DATA."
            load_screen.print_statement(message, None)
            load_screen.print_statement(
                f"Created: {created_counter} records.", "created"
            )
            load_screen.print_statement(
                f"Updated: {updated_counter} records.\n", "updated"
            )
            load_screen.print_statement(
                f"Invalid: {invalid_counter} records.\n", "invalid"
            )
