import argparse
import csv
import sys
from datetime import datetime

from django.core.management.base import BaseCommand

from university.core.accounts.models import Personnel, Religion, User
from university.framework.utils import LoadScreen

load_screen = LoadScreen()


class Command(BaseCommand):
    help = "Run personnel data upload functionality."

    def add_arguments(self, parser):
        parser.add_argument("csvfile", nargs="?", type=argparse.FileType("r"))

    def process_personnel(self, user, religion, row):
        birthdate = None
        if row.get("BIRTHDAY"):
            birthdate = datetime.strptime(row.get("BIRTHDAY"), "%m/%d/%Y")

        marriage_date = None
        if row.get("DATE_MARRIED"):
            marriage_date = datetime.strptime(row.get("DATE_MARRIED"), "%m/%d/%Y")

        separation_date = None
        if row.get("DATE_NOMARIED"):
            separation_date = datetime.strptime(row.get("DATE_NOMARIED"), "%m/%d/%Y")

        employment_date = None
        if row.get("EMPLOY_DATE"):
            employment_date = datetime.strptime(row.get("EMPLOY_DATE"), "%m/%d/%Y")

        student, created = Personnel.objects.update_or_create(
            user=user,
            defaults={
                "ref_id": row.get("IDNO"),
                "emp_id": row.get("EMP_ID"),
                "old_id": row.get("OLDID"),
                "first_name": row.get("FIRST"),
                "middle_name": row.get("MIDDLE"),
                "maiden_name": row.get("MAIDEN"),
                "last_name": row.get("LAST"),
                "birth_date": birthdate,
                "birth_place": row.get("BIRTHPLACE"),
                "gender": row.get("SEX"),
                "civil_status": row.get("CVSTAT"),
                "nationality": row.get("NATION_CD"),
                "spouse_name": row.get("SPOUSE"),
                "spouse_occupation": row.get("SPOUSE_OCC"),
                "no_of_child": row.get("CHILDREN") if row.get("CHILDREN") else 0,
                "sss_no": row.get("SSS_NO"),
                "tin": row.get("TIN"),
                "license_no": row.get("LICENSE"),
                "pagibig_no": row.get("PAGIBIG_NO"),
                "philhealth_no": row.get("PHILHEALTH_NO"),
                "phone_no": row.get("CELLNO"),
                "home_phone_no": row.get("PERM_TEL"),
                "local_address": row.get("BGO_ADDR"),
                "local_phone_no": row.get("BGO_TEL"),
                "street": row.get("STREET"),
                "barangay": row.get("BRGY"),
                "city": row.get("CT_CD"),
                "zip_code": row.get("ZIP_CD"),
                "relative_name": row.get("KIN"),
                "relative_relationship": row.get("KIN_REL"),
                "relative_address": row.get("KIN_ADDR"),
                "relative_phone_no": row.get("KIN_TEL"),
                "union_affiliation": row.get("UNION_AFF"),
                "employment_type": row.get("EMP_TYPE"),
                "tenure": row.get("TENURE"),
                "employee_status": row.get("EMP_STAT"),
                "father_name": row.get("FATHER"),
                "mother_name": row.get("MOTHER"),
                "marriage_date": marriage_date,
                "separation_date": separation_date,
                "employment_date": employment_date,
                "rank": row.get("RANK"),
                "religion": religion,
                "category": row.get("ID_CD"),
            },
        )

        return student

    def handle(self, *args, **options):
        with options["csvfile"] as csvfile:
            reader = csv.DictReader(csvfile)

            spinner = load_screen.spinning_cursor()
            sys.stdout.write("Personnel data upload... ")

            created_counter = 0
            updated_counter = 0
            invalid_counter = 0

            for row in reader:
                load_screen.spinner(spinner)

                emp_id = row.get("EMP_ID")

                # NOTE: All employee id that is less than 10 means inactive and won't be uploaded
                if int(emp_id) < 10:
                    print(f"Invalid Employee ID {emp_id}. ID Number: {row.get('IDNO')}")
                    invalid_counter += 1
                    continue

                id_code = row.get("ID_CD")
                username = f"{id_code}{emp_id}"
                if len(emp_id) < 4:
                    username = f"{id_code}{'0' * (4 - len(emp_id))}{emp_id}"

                user, created = User.objects.update_or_create(
                    username=username,
                    defaults={
                        "first_name": row.get("FIRST"),
                        "last_name": row.get("LAST"),
                        "status": User.Status.ACTIVE,
                        "is_staff": True,
                    },
                )

                religion = None
                if row.get("REL_CD"):
                    religion = Religion.objects.filter(code=row.get("REL_CD")).first()

                self.process_personnel(user, religion, row)

                if created:
                    created_counter += 1
                else:
                    updated_counter += 1

            message = f"\nSUCCESSFULLY PROCESSED {created_counter + updated_counter + invalid_counter} PERSONNEL DATA."
            load_screen.print_statement(message, None)
            load_screen.print_statement(
                f"Created: {created_counter} records.", "created"
            )
            load_screen.print_statement(
                f"Updated: {updated_counter} records.", "updated"
            )
            load_screen.print_statement(
                f"Invalid (employee ID less than 10): {invalid_counter} records.\n",
                "invalid",
            )
