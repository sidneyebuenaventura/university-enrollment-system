import argparse
import csv
import sys

from django.core.management.base import BaseCommand
from university.core.cms.models import (
    Curriculum,
    CurriculumPeriod,
    CurriculumSubject,
    Semesters,
    Subject,
)
from university.framework.utils import LoadScreen

load_screen = LoadScreen()

category_rate_mapping = {
    "1": CurriculumSubject.CategoryRates.PROFESSIONAL_EDUCATION,
    "2": CurriculumSubject.CategoryRates.NON_PROFESSIONAL,
    "3": CurriculumSubject.CategoryRates.IT_RATE,
    "4": CurriculumSubject.CategoryRates.NURSE_RATE,
    "5": CurriculumSubject.CategoryRates.LLB_RATE,
    "6": CurriculumSubject.CategoryRates.GRADUATE,
}

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
            sys.stdout.write(f"Curriculum Subject data upload... ")

            created_counter = 0
            updated_counter = 0
            invalid_counter = 0

            for row in reader:
                load_screen.spinner(spinner)

                curriculum = Curriculum.objects.filter(
                    ref_id=row.get("CURR_CD")
                ).first()

                if not curriculum:
                    print(f"Invalid Curriculum: {row.get('CURR_CD')}")
                    invalid_counter += 1
                    continue

                curriculum_period, created = CurriculumPeriod.objects.get_or_create(
                    curriculum=curriculum,
                    semester=sem_mapping.get(str(row.get("SEM"))),
                    year_level=int(row.get("YEAR")),
                )

                if not curriculum_period:
                    print(f"Invalid CurriculumPeriod: {row.get('CURR_CD')}")
                    invalid_counter += 1
                    continue

                subject = Subject.objects.filter(ref_id=row.get("SUBJ_CD")).first()

                if not subject:
                    print(f"Invalid Subject: {row.get('SUBJ_CD')}")
                    invalid_counter += 1
                    continue

                _, created = CurriculumSubject.objects.update_or_create(
                    curriculum_period=curriculum_period,
                    subject=subject,
                    defaults={
                        "curriculum": curriculum,
                        "subject_class": row.get("SUBJ_CLAS"),
                        "category_rate": category_rate_mapping.get(
                            str(row.get("CAT_RATE"))
                        ),
                        "lec_hrs": row.get("LEC") if row.get("LEC") else 0,
                        "lab_wk": row.get("LAB") if row.get("LAB") else 0,
                        "order": row.get("SEQ") if row.get("SEQ") else 0,
                    },
                )

                if created:
                    created_counter += 1
                else:
                    updated_counter += 1

            message = f"\nSUCCESSFULLY PROCESSED {invalid_counter+updated_counter+created_counter} CURRICULUM SUBJECT DATA."
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
