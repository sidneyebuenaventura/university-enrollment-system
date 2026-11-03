import argparse
import csv
import sys

from django.core.management.base import BaseCommand

from university.core.accounts.models import AcademicYear
from university.core.cms.models import Discount, Semesters
from university.core.students.models import Enrollment, Student
from university.framework.utils import LoadScreen

load_screen = LoadScreen()


sem_mapping = {
    "1": Semesters.FIRST_SEMESTER,
    "2": Semesters.SECOND_SEMESTER,
    "3": Semesters.SUMMER,
}


class Command(BaseCommand):
    help = "Run student data upload functionality"

    def add_arguments(self, parser):
        parser.add_argument("csvfile", nargs="?", type=argparse.FileType("r"))

    def handle(self, *args, **options):
        with options["csvfile"] as csvfile:
            reader = csv.DictReader(csvfile)

            updated_counter = 0
            invalid_discount_counter = 0
            invalid_student_counter = 0
            invalid_enrollment_counter = 0

            spinner = load_screen.spinning_cursor()
            sys.stdout.write("Enrollment Discount data upload... \n")

            for row in reader:
                # load_screen.spinner(spinner)

                student = Student.objects.filter(id_number=row.get("IDNO")).first()
                if not student:
                    print(f"Invalid Student: {row.get('IDNO')}")
                    invalid_student_counter += 1
                    continue

                discount = None
                if row.get("DISCD"):
                    discount = Discount.objects.filter(ref_id=row.get("DISCD")).first()
                    if not discount:
                        print(f"Invalid Discount Code: {row.get('DISCD')}")
                        invalid_discount_counter += 1
                        continue

                academic_year = AcademicYear.objects.filter(
                    year_start=int(row.get("TERM")[0:4]) - 1,
                    year_end=int(row.get("TERM")[0:4]),
                ).first()

                enrollment = Enrollment.objects.filter(
                    student=student,
                    academic_year=academic_year,
                    semester__term=sem_mapping.get(row.get("TERM")[4:]),
                ).first()

                if not enrollment:
                    print(f"Invalid Enrollment: {row.get('IDNO')} | {row.get('TERM')}")
                    invalid_enrollment_counter += 1
                    continue

                enrollment.discount = discount
                enrollment.save()

                updated_counter += 1

            total = (
                invalid_discount_counter
                + invalid_enrollment_counter
                + invalid_student_counter
                + updated_counter
            )

            message = f"\nSUCCESSFULLY PROCESSED {total} ENROLLMENT DISCOUNT DATA."
            load_screen.print_statement(message, None)
            load_screen.print_statement(
                f"Updated: {updated_counter} records.", "updated"
            )
            load_screen.print_statement(
                f"Invalid Student: {invalid_student_counter} records.", "invalid"
            )
            load_screen.print_statement(
                f"Invalid Discount: {invalid_discount_counter} records.", "invalid"
            )
            load_screen.print_statement(
                f"Invalid Enrollment: {invalid_enrollment_counter} records.\n",
                "invalid",
            )
