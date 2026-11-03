import argparse
import csv
import sys
from decimal import Decimal

from django.core.management.base import BaseCommand

from university.core.cms.models import Semesters
from university.core.students.models import Student
from university.core.students.selectors import enrollment_get_latest_enrolled
from university.framework.utils import LoadScreen
from university.payment.services import soa_create

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

            created_counter = 0
            invalid_student_counter = 0
            total_counter = 0
            invalid_enrollment_counter = 0

            spinner = load_screen.spinning_cursor()
            sys.stdout.write(f"Enrollment Outstanding Balance data upload... \n")

            for row in reader:
                total_counter += 1
                # load_screen.spinner(spinner)

                student = Student.objects.filter(id_number=row.get("IDNO")).first()
                if not student:
                    print(f"Invalid Student: {row.get('IDNO')}")
                    invalid_student_counter += 1
                    continue

                enrollment = enrollment_get_latest_enrolled(user=student.user)

                if not enrollment:
                    print(f"Invalid Enrollment: {row.get('IDNO')}")
                    invalid_enrollment_counter += 1
                    continue

                soa = soa_create(
                    enrollment=enrollment, discount_auto_apply=True, override=True
                )

                total_amount_paid = soa.get_remaining_balance() - Decimal(
                    row.get("REM_BALANCE")
                )
                if total_amount_paid > 0:
                    soa.transactions.create(
                        student=student,
                        description=f"System Uploaded Payment Transaction",
                        amount=-abs(total_amount_paid),
                    )

                if soa:
                    created_counter += 1

            message = f"\nSUCCESSFULLY PROCESSED {total_counter} ENROLLMENT OUTSTANDING BALANCE DATA."
            load_screen.print_statement(message, None)
            load_screen.print_statement(
                f"Generated SOA: {created_counter} records.", "created"
            )
            load_screen.print_statement(
                f"Invalid Student: {invalid_student_counter} records.", "invalid"
            )
            load_screen.print_statement(
                f"Invalid Enrollment: {invalid_enrollment_counter} records.\n",
                "invalid",
            )
