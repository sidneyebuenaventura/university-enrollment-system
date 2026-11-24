import argparse
import csv
import sys

from django.core.management.base import BaseCommand

from university.core.accounts.models import School
from university.core.cms.models import Subject, SubjectGrouping
from university.framework.utils import LoadScreen

load_screen = LoadScreen()

subject_unit_mapping = {
    "G": 6,
    "I": 21,
    "1": 1,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 7,
    "9": 9,
    "M": 0,
    "R": 3,
    "W": 0,
    "P": 0,
    "E": 10,
    "B": 1,
    "C": 2,
    "S": 4,
    "L": 14,
    "A": 0.5,
    "D": 12,
    "F": 1.5,
    "0": 0,
    "H": 18,
    "J": 15,
}


class Command(BaseCommand):
    help = "Run subject data upload functionality"

    def add_arguments(self, parser):
        parser.add_argument("csvfile", nargs="?", type=argparse.FileType("r"))

    def handle(self, *args, **options):
        with options["csvfile"] as csvfile:
            reader = csv.DictReader(csvfile)

            spinner = load_screen.spinning_cursor()
            sys.stdout.write("Subject data upload... ")

            created_counter = 0
            updated_counter = 0

            for row in reader:
                load_screen.spinner(spinner)

                school = None
                if row.get("GCOL"):
                    school = School.objects.filter(ref_id=row.get("GCOL")).first()

                grouping = None
                if row.get("GRP_CD"):
                    grouping = SubjectGrouping.objects.filter(
                        ref_id=row.get("GRP_CD")
                    ).first()

                units = 0
                if row.get("UNIT_CD"):
                    units = subject_unit_mapping[str(row.get("UNIT_CD"))]

                subject, created = Subject.objects.update_or_create(
                    ref_id=row.get("SUBJ_CD"),
                    defaults={
                        "school": school,
                        "grouping": grouping,
                        "charge_code": row.get("CHRGCD"),
                        "course_code": row.get("SC_CD"),
                        "course_number": row.get("SHORT_DESC"),
                        "descriptive_code": row.get("LD_CD"),
                        "descriptive_title": row.get("LONG_DESC"),
                        "is_professional_subject": row.get("PROFCD") in ["P"],
                        "is_lab_subject": row.get("LABCD") in ["A", "C", "G", "L"],
                        "lab_category": row.get("LABCD"),
                        "sub_type": row.get("SUB_T"),
                        "classification": row.get("CLASF"),
                        "units": units,
                        "no_of_hours": row.get("HRS") if row.get("HRS") else 0,
                        "duration": row.get("DUR"),
                    },
                )

                if created:
                    created_counter += 1
                else:
                    updated_counter += 1

            message = f"\nSUCCESSFULLY PROCESSED {created_counter + updated_counter} SUBJECT DATA."
            load_screen.print_statement(message, None)
            load_screen.print_statement(
                f"Created: {created_counter} records.", "created"
            )
            load_screen.print_statement(
                f"Updated: {updated_counter} records.\n", "updated"
            )
