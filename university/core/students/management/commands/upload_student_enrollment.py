import argparse
import csv
import sys

from django.core.management.base import BaseCommand

from university.core.accounts.models import AcademicYear
from university.core.cms.models import Semesters, Subject
from university.core.students.models import (
    Class,
    EnrolledClass,
    EnrolledClassGrade,
    Enrollment,
    EnrollmentGrade,
    EnrollmentStatus,
    GradeStates,
    Student,
)
from university.framework.utils import LoadScreen

load_screen = LoadScreen()

sem_mapping = {
    "1": Semesters.FIRST_SEMESTER,
    "2": Semesters.SECOND_SEMESTER,
    "3": Semesters.SUMMER,
}
status_mapping = {
    "PASSED": EnrolledClassGrade.Statuses.PASSED,
    "HIGH PASSED": EnrolledClassGrade.Statuses.HIGH_PASSED,
    "INCOMPLETE": EnrolledClassGrade.Statuses.INCOMPLETE,
    "INC": EnrolledClassGrade.Statuses.INCOMPLETE,
    "NOT COMPLETE": EnrolledClassGrade.Statuses.INCOMPLETE,
    "NO FINAL EXAMINATION": EnrolledClassGrade.Statuses.NO_FINAL_EXAMINATION,
    "YEARLY": EnrolledClassGrade.Statuses.YEARLY,
    "FAILED": EnrolledClassGrade.Statuses.FAILED,
    "WP": EnrolledClassGrade.Statuses.WITHDRAWAL_WITH_PERMISSION,
    "DROP": EnrolledClassGrade.Statuses.DROP,
}


class Command(BaseCommand):
    help = "Run student data upload functionality"
    created_counter = 0
    updated_counter = 0
    invalid_counter = 0
    is_submitted = 0

    def add_arguments(self, parser):
        parser.add_argument("csvfile", nargs="?", type=argparse.FileType("r"))
        parser.add_argument("is_preenrollment", default=0, type=int)
        parser.add_argument("is_submitted", default=0, type=int)

    def process_class_grade(self, enrolled_class, row):
        status = row.get("STATUS")
        try:
            grade = float(row.get("GRD_CD"))
        except (TypeError, ValueError):
            if row.get("GRD_CD") == "Y":
                status = "YEARLY"
            grade = None

        state = GradeStates.SUBMITTED if self.is_submitted else GradeStates.DRAFT

        prelim_grade_val = row.get("PLG")
        prelim_grade = (
            float(prelim_grade_val)
            if prelim_grade_val and prelim_grade_val.isnumeric()
            else 0
        )

        midterm_grade_val = row.get("MTG")
        midterm_grade = (
            float(midterm_grade_val)
            if midterm_grade_val and midterm_grade_val.isnumeric()
            else 0
        )

        tentative_final_grade_val = row.get("TFG")
        tentative_final_grade = (
            float(tentative_final_grade_val)
            if tentative_final_grade_val and tentative_final_grade_val.isnumeric()
            else 0
        )

        grade, _ = EnrolledClassGrade.objects.update_or_create(
            enrolled_class=enrolled_class,
            defaults={
                "prelim_grade": prelim_grade,
                "prelim_grade_state": state,
                "midterm_grade": midterm_grade,
                "midterm_grade_state": state,
                "tentative_final_grade": tentative_final_grade,
                "tentative_final_grade_state": state,
                "final_grade": grade,
                "final_grade_state": state,
                "status": status_mapping.get(status)
                or EnrolledClassGrade.Statuses.PENDING,
            },
        )

        return grade

    def process_enrollment_subject(self, enrollment, semester, student, row):
        klass = Class.objects.filter(
            class_code=row.get("CLASS_CODE"), semester=semester
        ).first()
        message = None

        if not klass:
            message = f"Invalid  Student No: {row.get('STUDENT NO')} Class Code: {row.get('CLASS_CODE')} - {row.get('TERM')}"
            return False, message

        subject = None
        if row.get("CURSTUD_SUBJ_EQV"):
            subject = Subject.objects.filter(ref_id=row.get("CURSTUD_SUBJ_EQV")).first()

            if not subject:
                message = f"Invalid  Student No: {row.get('STUDENT NO')} Equivalent Subject: {row.get('CURSTUD_SUBJ_EQV')}"
                return False, message

        curriculum_subject = enrollment.student.curriculum.subjects.filter(
            subject__ref_id=row.get("SUBJ_CD")
        ).first()

        # NOTE: Temp. If no curriculum subject match, SUBJ_CD should be treated as subject equivalent
        if not curriculum_subject:
            subject = None
            if row.get("SUBJ_CD"):
                subject = Subject.objects.filter(ref_id=row.get("SUBJ_CD")).first()

                if not subject:
                    message = f"Invalid  Student No: {row.get('STUDENT NO')} Curriculum Subject: {row.get('SUBJ_CD')} to Equivalent Subject: {row.get('SUBJ_CD')}"
                    return False, message
            else:
                message = f"Invalid  Student No: {row.get('STUDENT NO')} Curriculum Subject: {row.get('SUBJ_CD')} to Null Equivalent Subject"
                return False, message

        enrolled_class, _ = EnrolledClass.objects.update_or_create(
            enrollment=enrollment,
            klass=klass,
            defaults={
                "status": EnrolledClass.Statuses.APPROVED,
                "curriculum_subject": curriculum_subject,
                "equivalent_subject": subject,
                "student": student,
            },
        )

        grade = self.process_class_grade(enrolled_class, row)
        if grade:
            return True, message
        else:
            return False, message

    def process_enrollment_grade(self, enrollment):
        if not hasattr(enrollment, "grade"):
            EnrollmentGrade.objects.create(enrollment=enrollment)

    def handle(self, *args, **options):
        with options["csvfile"] as csvfile:
            reader = csv.DictReader(csvfile)

            is_preenrollment = options["is_preenrollment"]
            self.is_submitted = options["is_submitted"]

            sys.stdout.write("Student Enrollment data upload... \n")

            for row in reader:
                # load_screen.spinner(spinner)

                student = Student.objects.filter(
                    id_number=row.get("STUDENT NO")
                ).first()

                if not student:
                    print(f"Invalid Student No: {row.get('STUDENT NO')}")
                    self.invalid_counter += 1
                    continue

                academic_year, created = AcademicYear.objects.get_or_create(
                    year_start=int(row.get("SCHOOL_YR")[0:4]) - 1,
                    year_end=int(row.get("SCHOOL_YR")[0:4]),
                )

                semester = academic_year.semesters.filter(
                    term=sem_mapping.get(row.get("TERM"))
                ).first()

                enrollment, created = Enrollment.objects.get_or_create(
                    student=student,
                    academic_year=academic_year,
                    semester=semester,
                    defaults={
                        "step": Enrollment.Steps.STATUS,
                        "year_level": row.get("YEAR_LEVEL"),
                    },
                )

                if created:
                    status = Enrollment.Statuses.ENROLLED
                    step = Enrollment.Steps.PAYMENT
                    if is_preenrollment:
                        status = Enrollment.Statuses.PRE_ENROLLMENT
                        step = Enrollment.Steps.SUBJECTS
                    else:
                        EnrollmentStatus.objects.create(
                            enrollment=enrollment,
                            block_status=EnrollmentStatus.BlockStatuses.PASSED,
                        )

                    data = {
                        "status": status,
                        "step": step,
                        "academic_year": academic_year,
                        "current_address": student.address,
                        "contact_number": student.phone_no,
                        "personal_email": student.user.email,
                        "father_name": student.father_name,
                        "mother_name": student.mother_name,
                        "emergency_contact_name": student.guardian_name,
                        "emergency_contact_address": student.guardian_address,
                    }

                    enrollment.__dict__.update(**data)
                    enrollment.save()

                    self.process_enrollment_grade(enrollment=enrollment)

                enrolled_class, err = self.process_enrollment_subject(
                    enrollment, semester, student, row
                )

                if not enrolled_class:
                    self.invalid_counter += 1
                    print(err)
                    continue

                if created:
                    self.created_counter += 1
                else:
                    self.updated_counter += 1

            total = self.created_counter + self.updated_counter + self.invalid_counter
            message = f"\nSUCCESSFULLY PROCESSED {total} STUDENT_ENROLLMENT DATA."

            load_screen.print_statement(message, None)
            load_screen.print_statement(
                f"Created: {self.created_counter} records.", "created"
            )
            load_screen.print_statement(
                f"Updated: {self.updated_counter} records.", "updated"
            )
            load_screen.print_statement(
                f"Invalid: {self.invalid_counter} records.\n", "invalid"
            )
