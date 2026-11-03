import argparse
import csv
import sys
from datetime import datetime

from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand

from university.core.accounts.models import User
from university.core.cms.models import Curriculum
from university.core.students.models import Student
from university.framework.utils import LoadScreen

load_screen = LoadScreen()


class Command(BaseCommand):
    help = "Run student data upload functionality"
    invalid_counter = 0

    def add_arguments(self, parser):
        parser.add_argument("csvfile", nargs="?", type=argparse.FileType("r"))

    def process_student_information(self, user, row):
        birthdate = None
        if row.get("BDAY"):
            birthdate = datetime.strptime(row.get("BDAY"), "%m/%d/%Y")

            if birthdate > datetime.now():
                birthdate = birthdate - relativedelta(years=100)

        date_created = None
        if row.get("DEYT"):
            date_created = datetime.strptime(row.get("DEYT"), "%m/%d/%Y")

        curriculum = None
        if row.get("CURR_CD"):
            curriculum = Curriculum.objects.filter(ref_id=row.get("CURR_CD")).first()

        if not curriculum:
            self.invalid_counter += 1

        student, created = Student.objects.update_or_create(
            user=user,
            defaults={
                "type": Student.Types.STUDENT,
                "id_number": row.get("IDNO"),
                "applicant_number": row.get("CEENO"),
                "is_previous_number": row.get("PID") in ["Y"],
                "first_name": row.get("FIRST"),
                "middle_name": row.get("MID"),
                "last_name": row.get("LAST"),
                "birth_date": birthdate,
                "birth_place": row.get("BPLACE"),
                "civil_status": row.get("CVSTAT"),
                "citizenship": row.get("CITIZEN"),
                "nationality": row.get("NATION"),
                "street": row.get("STREET"),
                "barangay": row.get("BRGY"),
                "city": row.get("CT_CD"),
                "zip_code": row.get("ZIP_CD"),
                "phone_no": row.get("CELLNO"),
                "home_phone_no": row.get("H_TEL"),
                "local_address": row.get("B_ADDR"),
                "local_phone_no": row.get("B_TEL"),
                "guardian_name": row.get("G_ADDR"),
                "guardian_address": row.get("HOMEOF"),
                "father_name": row.get("FATHER"),
                "father_occupation": row.get("FWORK"),
                "mother_name": row.get("MOTHER"),
                "mother_occupation": row.get("MWORK"),
                "spouse_name": row.get("SPOUSE_NM"),
                "spouse_address": row.get("SPOUSE_ADDR"),
                "spouse_phone_no": row.get("SPOUSE_TEL"),
                "religion": row.get("REL_CD"),
                "senior_high_strand": row.get("STR_CODE"),
                "date_created": date_created,
                "curriculum": curriculum,
                "course": curriculum.course if curriculum else None,
            },
        )

        return student

    def handle(self, *args, **options):
        with options["csvfile"] as csvfile:
            reader = csv.DictReader(csvfile)

            spinner = load_screen.spinning_cursor()
            sys.stdout.write(f"Student data upload... ")

            created_counter = 0
            updated_counter = 0

            for row in reader:
                load_screen.spinner(spinner)

                user, created = User.objects.update_or_create(
                    username=row.get("IDNO"),
                    defaults={
                        "email": row.get("EMAILADDR"),
                        "first_name": row.get("FIRST"),
                        "last_name": row.get("LAST"),
                        "status": User.Status.ACTIVE,
                    },
                )

                self.process_student_information(user, row)

                if created:
                    created_counter += 1

                else:
                    updated_counter += 1

            total = created_counter + updated_counter + self.invalid_counter
            message = f"\nSUCCESSFULLY PROCESSED {total} STUDENT DATA."
            load_screen.print_statement(message, None)
            load_screen.print_statement(
                f"Created: {created_counter} records.", "created"
            )
            load_screen.print_statement(
                f"Updated: {updated_counter} records.", "updated"
            )
            load_screen.print_statement(
                f"No/Invalid Curriculum Code: {self.invalid_counter} records.\n",
                "invalid",
            )
