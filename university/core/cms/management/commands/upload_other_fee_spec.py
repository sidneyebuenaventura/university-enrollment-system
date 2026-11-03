import argparse
import csv
import sys

from django.core.management.base import BaseCommand

from university.core.accounts.models import AcademicYear, School
from university.core.cms.models import (
    Course,
    OtherFeeSpecification,
    Semesters,
    Subject,
    SubjectGrouping,
)
from university.core.students.models import Student
from university.framework.utils import LoadScreen

load_screen = LoadScreen()

sem_mapping = {
    "1": Semesters.FIRST_SEMESTER,
    "2": Semesters.SECOND_SEMESTER,
    "3": Semesters.SUMMER,
}

category_mapping = {
    "M": Course.Categories.MASTERAL,
    "D": Course.Categories.DOCTORAL,
}


student_type_mapping = {
    "1": Student.Types.FRESHMEN_APPLICANT,
    "2": Student.Types.STUDENT,
}


class Command(BaseCommand):
    help = "Run Other Fee Specification data upload functionality"

    def add_arguments(self, parser):
        parser.add_argument("csvfile", nargs="?", type=argparse.FileType("r"))

    def handle(self, *args, **options):
        with options["csvfile"] as csvfile:
            reader = csv.DictReader(csvfile)

            spinner = load_screen.spinning_cursor()
            sys.stdout.write(f"Other Fee Specification data upload... ")

            created_counter = 0
            updated_counter = 0

            for row in reader:
                load_screen.spinner(spinner)

                school = None
                if row.get("DEG1D"):
                    school = School.objects.filter(ref_id=row.get("DEG1D")).first()

                subject = None
                if row.get("CHRGCD"):
                    subject = Subject.objects.filter(
                        charge_code=row.get("CHRGCD")
                    ).first()

                subject_group = None
                if row.get("GRP_CD"):
                    subject_group = SubjectGrouping.objects.filter(
                        ref_id=row.get("GRP_CD")
                    ).first()

                if not row.get("SYRE"):
                    continue

                academic_year, created = AcademicYear.objects.get_or_create(
                    year_start=int(row.get("SYRE")[0:4]) - 1,
                    year_end=int(row.get("SYRE")[0:4]),
                )

                fee_spec, created = OtherFeeSpecification.objects.update_or_create(
                    code=row.get("OFCD"),
                    academic_year=academic_year,
                    defaults={
                        "school": school,
                        "subject": subject,
                        "subject_group": subject_group,
                        "semester_from": sem_mapping.get(str(row.get("SEMR1")))
                        or Semesters.FIRST_SEMESTER,
                        "semester_to": sem_mapping.get(str(row.get("SEMR2")))
                        or Semesters.SUMMER,
                        "year_level_from": row.get("YRR1") or 1,
                        "year_level_to": row.get("YRR1") or 5,
                        "description": row.get("MFDESC"),
                        "student_type": student_type_mapping.get(str(row.get("SNEW"))),
                        "course_category": category_mapping.get(str(row.get("DEGLVL"))),
                    },
                )

                fee_spec.fees.clear()

                if created:
                    created_counter += 1
                else:
                    updated_counter += 1

            message = f"\nSUCCESSFULLY PROCESSED {created_counter+updated_counter} OTHER FEE SPECIFICATION DATA."
            load_screen.print_statement(message, None)
            load_screen.print_statement(
                f"Created: {created_counter} records.", "created"
            )
            load_screen.print_statement(
                f"Updated: {updated_counter} records.\n", "updated"
            )
