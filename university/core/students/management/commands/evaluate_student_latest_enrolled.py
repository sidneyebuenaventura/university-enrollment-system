import sys

from django.core.management.base import BaseCommand, CommandError

from university.core.accounts.models import AcademicYear
from university.core.cms.models import Semesters
from university.core.students.models import Student
from university.core.students.selectors import enrollment_get_latest_enrolled
from university.framework.utils import LoadScreen
from university.core.students.services import enrollment_status_evaluate

load_screen = LoadScreen()


class Command(BaseCommand):
    help = (
        "Evaluate student's latest year level and semester after all enrollment upload"
    )

    def handle(self, *args, **options):
        spinner = load_screen.spinning_cursor()

        sys.stdout.write(f"Student Latest Enrollment evaluation... ")

        updated_counter = 0
        no_enrollment_counter = 0
        students = Student.objects.all()

        for student in students:
            load_screen.spinner(spinner)

            latest_enrolled = enrollment_get_latest_enrolled(user=student.user)
            if latest_enrolled:
                student.year_level = latest_enrolled.year_level
                student.semester = latest_enrolled.semester
                student.save()

                updated_counter += 1
            else:
                no_enrollment_counter += 1

        message = f"\nSUCCESSFULLY PROCESSED {updated_counter + no_enrollment_counter} STUDENT DATA.\n"
        load_screen.print_statement(message, None)
        load_screen.print_statement(f"Updated: {updated_counter} records.", "updated")
        load_screen.print_statement(
            f"No successful enrollment record: {no_enrollment_counter} records.\n",
            "invalid",
        )
