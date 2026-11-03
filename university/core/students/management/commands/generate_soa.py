import sys

from django.core.management.base import BaseCommand

from university.core.accounts.models import Semester
from university.core.students.models import Enrollment
from university.framework.utils import LoadScreen
from university.payment.services import soa_create

load_screen = LoadScreen()
sem_mapping = {
    "1": Semester.Terms.FIRST_SEMESTER,
    "2": Semester.Terms.SECOND_SEMESTER,
    "3": Semester.Terms.SUMMER,
}


class Command(BaseCommand):
    help = (
        "Generate SOA for all enrollments excluding the inputted specific AY and term"
    )

    def handle(self, *args, **options):
        spinner = load_screen.spinning_cursor()
        sys.stdout.write("Statement of account generation... ")
        counter = 0

        for enrollment in Enrollment.objects.all():
            # load_screen.spinner(spinner)
            if hasattr(enrollment, "statement_of_account"):
                continue

            soa = soa_create(enrollment=enrollment, discount_auto_apply=True)
            soa.transactions.create(
                student=enrollment.student,
                description="System Uploaded Payment Transaction",
                amount=-abs(soa.total_amount),
            )

            counter += 1

        message = f"\nSUCCESSFULLY PROCESSED {counter} ENROLLMENT DATA.\n"
        load_screen.print_statement(message, None)
