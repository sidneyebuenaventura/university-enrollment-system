import argparse
import csv
import sys
from decimal import Decimal

from django.core.management.base import BaseCommand

from university.core.accounts.models import AcademicYear
from university.core.cms.models import RemarkCode, Semesters
from university.core.students.models import Enrollment, EnrollmentGrade, Student
from university.framework.utils import LoadScreen
from university.core.students.services import enrollment_grade_process

load_screen = LoadScreen()


class Command(BaseCommand):
    help = "Run student data upload functionality"

    def add_arguments(self, parser):
        parser.add_argument("csvfile", nargs="?", type=argparse.FileType("r"))

    def handle(self, *args, **options):
        with options["csvfile"] as csvfile:
            reader = csv.DictReader(csvfile)

            updated_counter = 0
            invalid_counter = 0

            spinner = load_screen.spinning_cursor()
            sys.stdout.write(f"Enrollment GWA data upload... ")

            for row in reader:
                # load_screen.spinner(spinner)

                data = {
                    "id_no": row.get("IDNO"),
                    "school_year": row.get("SYEAR"),
                    "term": row.get("TERMSEM"),
                    "gwa": row.get("GWA"),
                    "pass_percentage": row.get("PERCENTPASSED"),
                    "remark_code": row.get("COMM_CD"),
                    "status": row.get("STATUS"),
                }

                result, err = enrollment_grade_process(data=data)
                if result:
                    updated_counter += 1
                else:
                    print(err)
                    invalid_counter += 1

            message = f"\nSUCCESSFULLY PROCESSED {updated_counter+invalid_counter} ENROLLMENT DISCOUNT DATA."
            load_screen.print_statement(message, None)
            load_screen.print_statement(
                f"Updated: {updated_counter} records.", "updated"
            )
            load_screen.print_statement(
                f"Invalid: {invalid_counter} records.\n", "invalid"
            )
