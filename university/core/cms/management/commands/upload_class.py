import argparse
import csv
import sys

from django.core.management.base import BaseCommand
from django.db import transaction

from university.core.accounts.models import AcademicYear, Personnel, Semester
from university.core.cms.models import Class, ClassSchedule, Room, Semesters, Subject, Course
from university.framework.utils import LoadScreen

load_screen = LoadScreen()

sem_mapping = {
    "1": Semesters.FIRST_SEMESTER,
    "2": Semesters.SECOND_SEMESTER,
    "3": Semesters.SUMMER,
}


class Command(BaseCommand):
    help = "Run schedule data upload functionality"

    created_counter = 0
    updated_counter = 0
    invalid_counter = 0
    invalid_term = 0
    invalid_course = 0
    invalid_subject = 0
    invalid_instructor_counter = 0
    total_counter = 0

    def add_arguments(self, parser):
        parser.add_argument("csvfile", nargs="?", type=argparse.FileType("r"))

    def process_days(self, day_code):
        days = []

        for day in ClassSchedule.Days.choices:
            if day[0] == ClassSchedule.Days.TUESDAY:
                n_code = day_code.replace("TH", "")
                if n_code and day[0] in n_code:
                    days.append(day)
            else:
                if day[0] in day_code:
                    days.append(day)

        return days

    def process_schedule_time(self, klass, row):
        room = None
        if row.get("ROOM"):
            room = Room.objects.filter(number=row.get("ROOM")).first()

        time_in = row.get("TIMEIN")
        time_out = row.get("TIMEOUT")

        time_in_val = row.get("TIMEIN")
        if time_in_val:
            if len(time_in_val) == 3:
                time_in_val = f"0{time_in_val}"
            time_in = time_in_val[:2] + ":" + time_in_val[2:]

        time_out_val = row.get("TIMEOUT")
        if time_out_val:
            if len(time_out_val) == 3:
                time_out_val = f"0{time_out_val}"
            time_out = time_out_val[:2] + ":" + time_out_val[2:]

        days = self.process_days(row.get("DAYCODE"))

        for day in days:
            _, created = ClassSchedule.objects.update_or_create(
                ref_id=row.get("SCHEDNO"),
                day=day[0],
                defaults={
                    "room": room,
                    "klass": klass,
                    "time_in": time_in,
                    "time_out": time_out,
                },
            )
        return

    def process_academic_year_set(self, year_start, year_end):
        academic_year, created = AcademicYear.objects.get_or_create(
            year_start=year_start,
            year_end=year_end,
        )

        semesters = [
            {"term": Semester.Terms.FIRST_SEMESTER, "order": 1},
            {"term": Semester.Terms.SECOND_SEMESTER, "order": 2},
            {"term": Semester.Terms.SUMMER, "order": 3},
        ]

        for sem in semesters:
            Semester.objects.update_or_create(
                academic_year=academic_year,
                term=sem.get("term"),
                defaults={"order": sem.get("order")},
            )

        return academic_year

    def process_chunk(self, chunk):
        for data in chunk:
            load_screen.spinner(self.spinner)

            self.total_counter += 1

            instructor = None
            if data.get("INST_CD"):
                instructor = Personnel.objects.filter(
                    ref_id=data.get("INST_CD")
                ).first()

                if not instructor:
                    print(
                        f"Invalid Instructor Code {data.get('INST_CD')} for class {data.get('CLAS_CD')} - {data.get('TERM')}."
                    )
                    self.invalid_instructor_counter += 1

            subject = None
            if data.get("SUBJ_CD"):
                subject = Subject.objects.filter(ref_id=data.get("SUBJ_CD")).first()

            if not subject:
                print(f"Invalid Subject: {data.get('SUBJ_CD')}")
                self.invalid_subject += 1
                continue

            course = None
            degree_code = data.get("DEG_CD", None)
            if degree_code:
                course = Course.objects.filter(code=degree_code).first()

            if not course:
                print(f"Invalid/Empty Course: {degree_code}")
                self.invalid_course += 1

            academic_year = self.process_academic_year_set(
                year_start=int(data.get("TERM")[0:4]) - 1,
                year_end=int(data.get("TERM")[0:4]),
            )

            semester, created = Semester.objects.get_or_create(
                academic_year=academic_year,
                term=sem_mapping.get(str(data.get("TERM")[4:])),
                defaults={"order": data.get("TERM")[4:]},
            )

            if not semester:
                print(f"Invalid Term: {data.get('TERM')}")
                self.invalid_term += 1
                continue

            klass, created = Class.objects.update_or_create(
                class_code=data.get("CLAS_CD"),
                subject=subject,
                semester=semester,
                defaults={
                    "course": course,
                    "instructor": instructor,
                    "class_size": data.get("NO_CARDS"),
                    "is_dissolved": data.get("DISSOLVED") in ["Y"],
                    "is_crash_course": data.get("CRASH_CORS") in ["Y"],
                    "is_intercollegiate": data.get("COL_ALLOWED") in ["Y"],
                    "is_external_class": data.get("CLAS_OUT") in ["Y"],
                    "remarks": data.get("CLAS_REM"),
                    "year_level": data.get("YEAR"),
                },
            )

            self.process_schedule_time(klass, data)

            if created:
                self.created_counter += 1
            else:
                self.updated_counter += 1

    def handle(self, *args, **options):
        with options["csvfile"] as csvfile:
            reader = csv.DictReader(csvfile)

            self.spinner = load_screen.spinning_cursor()
            sys.stdout.write(f"Class data upload... \n")

            chunk = []
            chunk_size = 1000

            for index, row in enumerate(reader):
                chunk.append(row)

                if index % chunk_size != 0:
                    continue

                # By committing updates in a transaction, we only reach the db
                # once every `chunk_size`.
                with transaction.atomic():
                    self.process_chunk(chunk)

                # Reset chunk
                chunk = []

            # Process remaining chunk
            self.process_chunk(chunk)

            message = f"\nSUCCESSFULLY PROCESSED {self.total_counter} CLASS DATA."
            load_screen.print_statement(message, None)
            load_screen.print_statement(
                f"Created: {self.created_counter} records.", "created"
            )
            load_screen.print_statement(
                f"Updated: {self.updated_counter} records.", "updated"
            )
            load_screen.print_statement(
                f"Invalid Instructor: {self.invalid_instructor_counter} records.",
                "invalid",
            )
            load_screen.print_statement(
                f"Invalid Course: {self.invalid_course} records.", "invalid"
            )
            load_screen.print_statement(
                f"Invalid Subject: {self.invalid_subject} records.", "invalid"
            )
            load_screen.print_statement(
                f"Invalid Term: {self.invalid_term} records.\n", "invalid"
            )
