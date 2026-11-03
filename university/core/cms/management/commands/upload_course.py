import argparse
import csv
import sys

from django.core.management.base import BaseCommand

from university.core.accounts.models import School
from university.core.cms.models import Course
from university.framework.utils import LoadScreen

load_screen = LoadScreen()

category_mapping = {
    "MEDICAL LABORATORY SCIENCE": Course.Categories.MEDICAL_LABORATORY_SCIENCE,
    "MASTERAL": Course.Categories.MASTERAL,
    "BUSINESS ADMINISTRATION": Course.Categories.BUSINESS_ADMINISTRATION,
    "HOSPITALITY AND TOURISM MGMT.": Course.Categories.HOSPITALITY_AND_TOURISM_MANAGEMENT,
    "PHILOSOPHY": Course.Categories.PHILOSOPHY,
    "EDUCATION": Course.Categories.EDUCATION,
    "ENGLISH": Course.Categories.ENGLISH,
    "LAW": Course.Categories.LAW,
    "MEDICAL TECHNOLOGY": Course.Categories.MEDICAL_TECHNOLOGY,
    "ACCOUNTANCY": Course.Categories.ACCOUNTANCY,
    "DOCTORAL": Course.Categories.DOCTORAL,
    "MATHEMATICS": Course.Categories.MATHEMATICS,
    "ENGINEERING": Course.Categories.ENGINEERING,
    "RADIOLOGIC TECHNOLOGY": Course.Categories.RADIOLOGIC_TECHNOLOGY,
    "INFO TECHNOLOGY": Course.Categories.INFO_TECHNOLOGY,
    "COMMERCE": Course.Categories.COMMERCE,
    "ARCHITECTURE": Course.Categories.ARCHITECTURE,
    "COMPUTER SCIENCE": Course.Categories.COMPUTER_SCIENCE,
    "AB": Course.Categories.AB,
    "ECONOMICS": Course.Categories.ECONOMICS,
    "LITERATURE": Course.Categories.LITERATURE,
    "HOSPITALITY AND TOURISM MGMT": Course.Categories.HOSPITALITY_AND_TOURISM_MANAGEMENT,
    "BIOLOGY": Course.Categories.BIOLOGY,
    "LEGAL STUDIES": Course.Categories.LEGAL_STUDIES,
    "COMMUNICATION": Course.Categories.COMMUNICATION,
    "POLITICAL SCIENCE": Course.Categories.POLITICAL_SCIENCE,
    "INTERDISCIPLINARY STUDIES": Course.Categories.INTERDISCIPLINARY_STUDIES,
    "STATISTICS": Course.Categories.STATISTICS,
    "PSYCHOLOGY": Course.Categories.PSYCHOLOGY,
    "SOCIAL WORK": Course.Categories.SOCIAL_WORK,
    "SOCIOLOGY": Course.Categories.SOCIOLOGY,
    "PHARMACY": Course.Categories.PHARMACY,
    "NURSING": Course.Categories.NURSING,
    "MEDICINE": Course.Categories.MEDICINE,
}


class Command(BaseCommand):
    help = "Run course data upload functionality"

    def add_arguments(self, parser):
        parser.add_argument("csvfile", nargs="?", type=argparse.FileType("r"))

    def handle(self, *args, **options):
        with options["csvfile"] as csvfile:
            reader = csv.DictReader(csvfile)

            spinner = load_screen.spinning_cursor()
            sys.stdout.write(f"Course data upload... ")

            created_counter = 0
            updated_counter = 0

            for row in reader:
                load_screen.spinner(spinner)

                school = None
                if row.get("COLL_CD"):
                    school = School.objects.filter(ref_id=row.get("COLL_CD")).first()

                course, created = Course.objects.update_or_create(
                    code=row.get("DEG_CD"),
                    defaults={
                        "school": school,
                        "sub_code": row.get("DEGREE"),
                        "name": row.get("LD_DEG"),
                        "major": row.get("MAJOR"),
                        "minor": row.get("MINOR"),
                        "is_accredited": row.get("ACCRED") in ["Y"],
                        "accredited_year": row.get("ACRDYR"),
                        "has_board_exam": row.get("ACCRED") in ["Y"],
                        "is_active": row.get("STATUS") in [""],
                        "duration": row.get("DURATION"),
                        "duration_unit": row.get("UNIT_OF_DUR"),
                        "level": row.get("DEG_LEVEL"),
                        "category": category_mapping.get(row.get("COURSE")),
                        "degree_class": row.get("DEGCLAS"),
                    },
                )

                if created:
                    created_counter += 1
                else:
                    updated_counter += 1

            message = f"\nSUCCESSFULLY PROCESSED {created_counter + updated_counter} COURSE DATA."
            load_screen.print_statement(message, None)
            load_screen.print_statement(
                f"Created: {created_counter} records.", "created"
            )
            load_screen.print_statement(
                f"Updated: {updated_counter} records.\n", "updated"
            )
