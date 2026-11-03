import sys

from django.core.management.base import BaseCommand, CommandError

from university.core.accounts.models import AcademicYear
from university.core.cms.models import Semesters
from university.framework.utils import LoadScreen
from university.core.students.services import enrollment_status_evaluate

load_screen = LoadScreen()


class Command(BaseCommand):
    help = "Generate SOA for enrollment data of 20222 and below"

    def handle(self, *args, **options):
        spinner = load_screen.spinning_cursor()

        sys.stdout.write(f"Enrollment Status evaluation... ")

        counter = 0
        academic_year = AcademicYear.objects.filter(year_end=2023).first()
        semester = academic_year.semesters.filter(term=Semesters.FIRST_SEMESTER).first()

        for enrollment in semester.enrollments.all():
            load_screen.spinner(spinner)
            enrollment_status_evaluate(enrollment=enrollment)

            counter += 1

        message = f"\nSUCCESSFULLY PROCESSED {counter} ENROLLMENT DATA.\n"
        load_screen.print_statement(message, None)
