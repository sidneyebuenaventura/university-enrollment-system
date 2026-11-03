import csv
from decimal import Decimal
from random import choice

import botocore.exceptions
from django.contrib.auth import get_user_model
from django.core.files import File
from django.db import transaction
from openpyxl import load_workbook
from rest_framework import exceptions
from sentry_sdk import capture_exception

from university.core import events
from university.core.accounts.constants import ReservedRole
from university.core.accounts.models import AcademicYear, Personnel, Role
from university.core.accounts.selectors import (
    current_academic_year_get,
    next_semester_get,
)
from university.core.accounts.services import user_role_remove
from university.core.cms.models import (
    Class,
    Course,
    Curriculum,
    CurriculumPeriod,
    Discount,
    MiscellaneousFeeSpecification,
    OtherFeeSpecification,
    RemarkCode,
    Semesters,
)
from university.core.cms.services import class_grade_state_update
from university.framework.events import event_publisher
from university.framework.exceptions import ServiceException
from university.framework.utils import get_random_string
from university.payment.models import (
    BukasTransaction,
    CashierTransaction,
    DragonpayTransaction,
    OverTheCounterTransaction,
)
from university.payment.selectors import soa_get_paid_amount

from . import models, tasks
from .selectors import (
    enrollment_get_latest_enrolled,
    student_has_failed_subject_get,
    student_has_remaining_balance_get,
)

User = get_user_model()


def student_password_generate(*, student: models.Student, override: bool = False):
    user = student.user

    if user.password and not override:
        return

    password = get_random_string()
    user.set_password(password)
    user.save()

    event_publisher.generic(
        events.STUDENT_PASSWORD_GENERATED, object=student, password=password
    )


def enrollment_create(*, student: models.Student, data: dict) -> models.Enrollment:
    semester = next_semester_get()
    latest_enrolled = enrollment_get_latest_enrolled(user=student.user)
    current_academic_year = current_academic_year_get()

    if not latest_enrolled:
        year_level = 1
    else:
        if (
            semester.academic_year == current_academic_year_get()
            and latest_enrolled.academic_year == current_academic_year
        ):
            year_level = latest_enrolled.year_level
        else:
            year_level = latest_enrolled.year_level + 1

    enrollment = models.Enrollment.objects.create(
        student=student,
        semester=semester,
        academic_year=semester.academic_year,
        year_level=year_level,
        status=models.Enrollment.Statuses.ENROLLMENT,
        **data,
    )

    models.EnrollmentDiscount.objects.create(enrollment=enrollment)

    return enrollment


def _enrollment_update(*, enrollment: models.Enrollment, data: dict):
    for key, value in data.items():
        setattr(enrollment, key, value)

    enrollment.save()


@transaction.atomic
def enrollment_step_1_information(*, enrollment: models.Enrollment, data: dict):
    if enrollment.status == models.Enrollment.Statuses.ENROLLMENT:
        enrollment.events.get_or_create(
            event=models.EnrollmentEvent.Events.ENROLLMENT_STARTED
        )

    _enrollment_update(enrollment=enrollment, data=data)

    student = enrollment.student
    student.phone_no = data.get("contact_number", student.phone_no)
    student.user.email = data.get("institutional_email", student.user.email)
    student.institutional_email = data.get(
        "institutional_email", student.institutional_email
    )
    student.email = data.get("personal_email", student.email)
    student.father_name = data.get("father_name", student.father_name)
    student.father_occupation = data.get("father_occupation", student.father_occupation)
    student.mother_name = data.get("mother_name", student.mother_name)
    student.mother_occupation = data.get("mother_occupation", student.mother_occupation)
    student.emergency_contact_name = data.get(
        "emergency_contact_name", student.emergency_contact_name
    )
    student.emergency_contact_address = data.get(
        "emergency_contact_address", student.emergency_contact_address
    )
    student.emergency_contact_email = data.get(
        "emergency_contact_email", student.emergency_contact_email
    )
    student.emergency_contact_phone_no = data.get(
        "emergency_contact_phone_no", student.emergency_contact_phone_no
    )

    student.user.save()
    student.save()


@transaction.atomic
def enrollment_step_2_discounts(*, enrollment: models.Enrollment, data: dict):
    personnel = None
    if data.get("is_employee"):
        personnel = Personnel.objects.filter(
            user__username=data.get("employee_no")
        ).first()

    dependent_personnel = None
    if data.get("is_employee_dependent"):
        dependent_personnel = Personnel.objects.filter(
            user__username=data.get("dependent_employee_no")
        ).first()

    siblings = None
    if data.get("has_enrolled_sibling"):
        siblings = models.Student.objects.filter(
            id_number__in=data.get("sibling_student_numbers")
        )

    if not hasattr(enrollment, "discounts"):
        models.EnrollmentDiscount.objects.create(enrollment=enrollment)

    discount = enrollment.discounts
    discount.is_employee = data.get("is_employee")
    discount.personnel = personnel
    discount.is_employee_dependent = data.get("is_employee_dependent")
    discount.dependent_personnel = dependent_personnel
    discount.dependent_relationship = data.get("dependent_relationship")
    discount.is_working_scholar = data.get("is_working_scholar")
    discount.has_enrolled_sibling = data.get("has_enrolled_sibling")

    if siblings:
        discount.siblings.clear()
        discount.siblings.add(*siblings)

    discount.save()

    _enrollment_update(enrollment=enrollment, data={"step": data.get("step")})


@transaction.atomic
def enrollment_step_3_subjects(*, enrollment: models.Enrollment, data: dict):
    from university.payment.services import soa_create

    # NOTE: Adjustments of enrollment subjects are allowed up to step 4
    enrollment.enrolled_classes.all().delete()

    for klass in data.get("enrolled_classes"):
        enrolled_class_data = {
            "student": enrollment.student,
            "enrollment": enrollment,
            "klass": klass.get("klass"),
            "curriculum_subject": klass.get("curriculum_subject"),
            "status": models.EnrolledClass.Statuses.RESERVED,
        }

        models.EnrolledClass.objects.create(**enrolled_class_data)

    _enrollment_update(enrollment=enrollment, data={"step": data.get("step")})
    soa_create(enrollment=enrollment, override=True)


def enrollment_step_4_payments(*, enrollment: models.Enrollment, data: dict):
    _enrollment_update(enrollment=enrollment, data=data)


def enrollment_step_5_status_check(*, enrollment: models.Enrollment, data: dict):
    # TODO: deprecated
    soa = enrollment.statement_of_account
    paid_amount = soa_get_paid_amount(soa=soa)

    if paid_amount >= soa.get_min_amount_due():
        enrollment.status = models.Enrollment.Statuses.ENROLLED
        enrollment.save()

        user_role_remove(
            role_key=ReservedRole.STUDENT_ENROLLMENT, user=enrollment.student.user
        )


def enrollment_enrolled(*, enrollment: models.Enrollment):
    enrollment.status = models.Enrollment.Statuses.ENROLLED
    enrollment.save()

    user_role_remove(
        role_key=ReservedRole.STUDENT_ENROLLMENT, user=enrollment.student.user
    )

    event_publisher.generic(events.ENROLLMENT_ENROLLED, object=enrollment)


def enrollment_update(*, enrollment: models.Enrollment, data: dict):
    status_display = enrollment.get_status_display()

    if enrollment.status not in models.Enrollment.ONGOING_STATUSES:
        raise exceptions.PermissionDenied(
            f'Updates are not allowed on status "{status_display}".'
        )

    step = data.get("step")

    if (
        enrollment.status == models.Enrollment.Statuses.PRE_ENROLLMENT
        and step not in models.Enrollment.PRE_ENROLLMENT_STEPS
    ) or (
        enrollment.status == models.Enrollment.Statuses.ENROLLMENT
        and step not in models.Enrollment.ENROLLMENT_STEPS
    ):
        raise exceptions.PermissionDenied(
            f'Updates on Step {step} are not allowed on status "{status_display}".'
        )

    methods = {
        models.Enrollment.Steps.INFORMATION: enrollment_step_1_information,
        models.Enrollment.Steps.DISCOUNTS: enrollment_step_2_discounts,
        models.Enrollment.Steps.SUBJECTS: enrollment_step_3_subjects,
        models.Enrollment.Steps.PAYMENT: enrollment_step_4_payments,
        models.Enrollment.Steps.STATUS: enrollment_step_5_status_check,
    }

    method = methods.get(step)

    if method:
        method(enrollment=enrollment, data=data)


def enrollment_status_update(*, data: dict) -> None:
    enrollments = models.Enrollment.objects.filter(id__in=data.get("enrollment_ids"))
    enrollment_role = Role.objects.filter(name=ReservedRole.STUDENT_ENROLLMENT).first()

    for enrollment in enrollments:
        if hasattr(enrollment, "enrollmentstatus"):
            enrollment.status = data.get("status")
            enrollment.save()

            enrollment.enrollmentstatus.is_temporary_allowed = data.get(
                "is_temporary_allowed"
            )
            enrollment.enrollmentstatus.save()

            if enrollment.status == models.Enrollment.Statuses.PRE_ENROLLED:
                enrollment.student.user.groups.add(enrollment_role)
            else:
                enrollment.student.user.groups.remove(enrollment_role)


def enrollment_remark_update(*, data: dict) -> None:
    enrollments = models.Enrollment.objects.filter(id__in=data.get("enrollment_ids"))

    for enrollment in enrollments:
        if hasattr(enrollment, "enrollmentstatus"):
            enrollment.enrollmentstatus.is_for_manual_tagging = True
            enrollment.enrollmentstatus.evaluation_remarks = data.get(
                "evaluation_remarks"
            )
            enrollment.enrollmentstatus.remark_code = data.get("remark_code")
            enrollment.enrollmentstatus.save()


def test_student_create(
    *,
    username: str,
    email: str,
    first_name: str,
    last_name: str,
    student_number: str,
):
    from university.payment.services import soa_create

    user, created = User.objects.update_or_create(
        username=username,
        defaults={
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
        },
    )

    if created:
        user.set_password("testpassword")
        user.save()

    models.Student.objects.update_or_create(
        user=user,
        defaults={
            "type": models.Student.Types.STUDENT,
            "id_number": student_number,
            "applicant_number": None,
            "is_previous_number": None,
            "first_name": first_name,
            "middle_name": "",
            "last_name": last_name,
            "birth_date": "2000-01-01",
            "birth_place": "Sample City",
            "civil_status": models.Student.CivilStatuses.SINGLE,
            "citizenship": models.Student.Citizenships.Filipino,
            "nationality": models.Student.Nationalities.Filipino,
            "religion": None,
            "senior_high_strand": None,
            "street": "#001 Street",
            "barangay": "Brgy. Barangay",
            "city": "Sample City",
            "zip_code": "2600",
            "phone_no": "0212345678",
            "home_phone_no": "09987654321",
            "local_address": "Sample City",
            "local_phone_no": "09123456789",
            "guardian_name": None,
            "guardian_address": None,
            "father_name": "Miguel dela Cruz",
            "father_occupation": None,
            "mother_name": "Maria dela Cruz",
            "mother_occupation": None,
            "spouse_name": None,
            "spouse_address": None,
            "spouse_phone_no": None,
            "date_created": None,
        },
    )

    enrollments = [
        {
            "school_year": (2020, 2021),
            "year_level": 1,
            "semester": Semesters.FIRST_SEMESTER,
            "is_ongoing": False,
        },
        {
            "school_year": (2020, 2021),
            "year_level": 1,
            "semester": Semesters.SECOND_SEMESTER,
            "is_ongoing": False,
        },
        {
            "school_year": (2021, 2022),
            "year_level": 2,
            "semester": Semesters.FIRST_SEMESTER,
            "is_ongoing": False,
        },
        {
            "school_year": (2021, 2022),
            "year_level": 2,
            "semester": Semesters.SECOND_SEMESTER,
            "is_ongoing": True,
        },
        {
            "school_year": (2021, 2022),
            "year_level": 2,
            "semester": Semesters.SUMMER,
            "is_ongoing": False,
        },
    ]

    for enrollment_data in enrollments:
        student = user.student
        course_sub_code = "BSCS"
        course = Course.objects.filter(sub_code=course_sub_code).first()

        if not course:
            raise ServiceException(f"Course {course_sub_code} not found.")

        latest_curriculum = (
            Curriculum.objects.filter(course=course)
            .order_by("-effective_start_year")
            .first()
        )

        if not latest_curriculum:
            raise ServiceException(
                f"No available curriculum for course {course_sub_code}."
            )

        curriculum_period = CurriculumPeriod.objects.filter(
            curriculum=latest_curriculum,
            semester=enrollment_data["semester"],
            year_level=enrollment_data["year_level"],
        ).first()

        if not curriculum_period:
            raise ServiceException(
                f"No available curriculum period for curriculum {latest_curriculum}."
            )

        enrollment_status = models.Enrollment.Statuses.ENROLLED
        enrollment_step = models.Enrollment.Steps.STATUS

        if enrollment_data["is_ongoing"]:
            enrollment_status = models.Enrollment.Statuses.ENROLLMENT
            enrollment_step = models.Enrollment.Steps.SUBJECTS

        academic_year, _ = AcademicYear.objects.get_or_create(
            year_start=enrollment_data["school_year"][0],
            year_end=enrollment_data["school_year"][1],
        )

        semester = academic_year.semesters.filter(
            term=enrollment_data["semester"]
        ).first()

        misc_fee_spec = MiscellaneousFeeSpecification.active_objects.filter(
            academic_year=academic_year
        ).first()

        other_fee_spec = OtherFeeSpecification.active_objects.filter(
            academic_year=academic_year
        ).first()

        discount = Discount.active_objects.filter(ref_id="13").first()

        enrollment, _ = models.Enrollment.objects.update_or_create(
            student=student,
            semester=semester,
            defaults={
                "status": enrollment_status,
                "step": enrollment_step,
                "academic_year": academic_year,
                "year_level": enrollment_data["year_level"],
                "current_address": student.address,
                "contact_number": student.home_phone_no,
                "personal_email": user.email,
                "institutional_email": user.email,
                "father_name": student.father_name,
                "father_phone_no": "09123456789",
                "father_email": "migueldelacruz@example.com",
                "mother_name": student.mother_name,
                "mother_phone_no": "09987654321",
                "mother_email": "mariadelacruz@example.com",
                "is_living_with_parents": True,
                "emergency_contact_name": "Maria dela Cruz",
                "emergency_contact_address": "Sample City",
                "emergency_contact_phone_no": "09987654321",
                "emergency_contact_email": "mariadelacruz@example.com",
                "miscellaneous_fee_specification": misc_fee_spec,
                "other_fee_specification": other_fee_spec,
            },
        )

        if not hasattr(enrollment, "discounts"):
            models.EnrollmentDiscount.objects.create(
                enrollment=enrollment,
                is_employee=False,
                personnel=None,
                is_employee_dependent=False,
                dependent_personnel=None,
                dependent_relationship=None,
                is_working_scholar=False,
                has_enrolled_sibling=False,
                validated_discount=discount,
            )

        if not hasattr(enrollment, "enrollmentstatus"):
            models.EnrollmentStatus.objects.create(
                enrollment=enrollment,
                block_status=models.EnrollmentStatus.BlockStatuses.PASSED,
            )

        enrollment.enrolled_classes.all().delete()

        student.course = latest_curriculum.course
        student.curriculum = latest_curriculum
        student.save()

        for curriculum_subject in curriculum_period.curriculum_subjects.all():
            subject_classes = list(
                Class.objects.filter(
                    semester=semester, subject=curriculum_subject.subject
                )
            )

            if not subject_classes:
                continue

            klass = choice(subject_classes)
            enrolled_class = enrollment.enrolled_classes.create(
                klass=klass,
                curriculum_subject=curriculum_subject,
                student=student,
                status=models.EnrolledClass.Statuses.APPROVED,
            )

            grade, _ = models.EnrolledClassGrade.objects.update_or_create(
                enrolled_class=enrolled_class,
                defaults={
                    "prelim_grade": 90,
                    "midterm_grade": 80,
                    "tentative_final_grade": 95,
                    "final_grade": 95,
                    "status": models.EnrolledClassGrade.Statuses.PASSED,
                },
            )

        soa = soa_create(enrollment=enrollment, override=True)

        DragonpayTransaction.objects.filter(soa__user=user).delete()
        BukasTransaction.objects.filter(soa__user=user).delete()
        OverTheCounterTransaction.objects.filter(soa__user=user).delete()
        CashierTransaction.objects.filter(soa__user=user).delete()

        if not enrollment_data["is_ongoing"]:
            otc_transaction = OverTheCounterTransaction.objects.create(
                soa=soa,
                amount=soa.total_amount,
                status=OverTheCounterTransaction.Statuses.SUCCESS,
            )
            otc_transaction.generate_id()

    roles = [ReservedRole.STUDENT, ReservedRole.STUDENT_ENROLLMENT]

    for key in roles:
        role = Role.objects.get_by_natural_key(key)
        user.groups.add(role)


def enrollment_status_evaluate(*, enrollment: models.Enrollment):
    from university.payment.services import soa_create

    student = enrollment.student

    has_failed = student_has_failed_subject_get(student=student)
    has_balance = student_has_remaining_balance_get(user=student.user)

    status = models.EnrollmentStatus.BlockStatuses.PASSED
    is_for_manual_tagging = False

    block_statuses = [
        models.EnrollmentStatus.BlockStatuses.BLOCKED_WITH_OUTSTANDING_AND_FAILED_GRADE,
        models.EnrollmentStatus.BlockStatuses.BLOCKED_WITH_FAILED_SUBJECT,
        models.EnrollmentStatus.BlockStatuses.BLOCKED_WITH_OUTSTANDING_BALANCE,
    ]

    if has_failed and has_balance:
        status = models.EnrollmentStatus.BlockStatuses.BLOCKED_WITH_OUTSTANDING_AND_FAILED_GRADE
    elif has_failed:
        status = models.EnrollmentStatus.BlockStatuses.BLOCKED_WITH_FAILED_SUBJECT
    elif has_balance:
        is_for_manual_tagging = True
        status = models.EnrollmentStatus.BlockStatuses.BLOCKED_WITH_OUTSTANDING_BALANCE

    if status in block_statuses:
        if hasattr(enrollment, "enrollmentstatus"):
            if status is not enrollment.enrollmentstatus.block_status:
                # TODO: Send email notification
                pass
        else:
            # TODO: Send email notification
            pass
    else:
        latest_enrolled = enrollment_get_latest_enrolled(user=student.user)
        credits = 0
        if latest_enrolled and hasattr(latest_enrolled, "statement_of_account"):
            credits = latest_enrolled.statement_of_account.get_available_credits()

            # NOTE: Even out transaction for latest enrolled
            if credits > 0:
                latest_enrolled.statement_of_account.transactions.create(
                    student=enrollment.student,
                    description="System Uploaded Payment Transaction - Carry over available credits to newest enrollment",
                    amount=credits,
                )

        soa = soa_create(enrollment=enrollment)

        # NOTE: Carry over previous credits to newly created SOA
        if credits > 0:
            soa.transactions.create(
                student=enrollment.student,
                description="System Uploaded Payment Transaction - Available credits from previous enrollment",
                amount=-abs(credits),
            )

        enrollment.status = models.Enrollment.Statuses.PRE_ENROLLED
        enrollment.save()

    models.EnrollmentStatus.objects.update_or_create(
        enrollment=enrollment,
        defaults={
            "block_status": status,
            "is_for_manual_tagging": is_for_manual_tagging,
        },
    )

    return enrollment


def grade_sheet_process(*, grade_sheet: models.GradeSheet):
    columns = [
        "STUDENT NO",  # 0
        "CLASS CODE",  # 1
        "SUBJECT CODE",  # 2
        "SUBJECT NAME",  # 3
        "UNITS",  # 4
        "SCHOOL_YR",  # 5
        "TERM",  # 6
        "PRELIM GRADE",  # 7
        "MIDTERM GRADE",  # 8
        "TENTATIVE FINAL GRADE",  # 9
        "MED_GRD_CD",  # 10
        "MED_STATUS",  # 11
        "GRD_CD",  # 12
        "STATUS",  # 13
    ]

    grade_sheet.status = models.GradeSheet.Statuses.PROCESSING
    grade_sheet.save()

    workbook = load_workbook(grade_sheet.file)
    worksheets = list(workbook)

    if len(worksheets) == 0:
        grade_sheet.status = models.GradeSheet.Statuses.FAILED
        grade_sheet.error_message = "Empty file."
        grade_sheet.save()
        return

    worksheet = worksheets[0]

    for index, row in enumerate(worksheet):
        if index == 0:
            for cell in row:
                if cell.value not in columns:
                    grade_sheet.status = models.GradeSheet.Statuses.FAILED
                    grade_sheet.error_message = f"Invalid column {cell.value}"
                    grade_sheet.save()
                    return

        cells = list(row)
        student = models.Student.objects.filter(id_number=cells[0].value).first()

        if not student:
            continue

        status = models.GradeStatuses.PENDING
        status_label = cells[13].value

        for grade_status in models.GradeStatuses:
            if grade_status.label == status_label:
                status = grade_status
                break

        data = {}

        enrolled_class_grade = models.EnrolledClassGrade.objects.filter(
            enrolled_class__student=student, enrolled_class__klass=grade_sheet.klass
        ).first()

        if enrolled_class_grade:
            if (
                enrolled_class_grade.prelim_grade_state
                in models.EnrolledClassGrade.EDITABLE_GRADE_STATES
            ):
                data["prelim_grade"] = cells[7].value or None
            else:
                data["prelim_grade"] = enrolled_class_grade.prelim_grade
                data["prelim_grade_state"] = enrolled_class_grade.prelim_grade_state

            if (
                enrolled_class_grade.midterm_grade_state
                in models.EnrolledClassGrade.EDITABLE_GRADE_STATES
            ):
                data["midterm_grade"] = cells[8].value or None
            else:
                data["midterm_grade"] = enrolled_class_grade.midterm_grade
                data["midterm_grade_state"] = enrolled_class_grade.midterm_grade_state

            if (
                enrolled_class_grade.tentative_final_grade_state
                in models.EnrolledClassGrade.EDITABLE_GRADE_STATES
            ):
                data["tentative_final_grade"] = cells[9].value or None
            else:
                data["tentative_final_grade"] = (
                    enrolled_class_grade.tentative_final_grade
                )
                data["tentative_final_grade_state"] = (
                    enrolled_class_grade.tentative_final_grade_state
                )

            if (
                enrolled_class_grade.final_grade_state
                in models.EnrolledClassGrade.EDITABLE_GRADE_STATES
            ):
                data["final_grade"] = cells[12].value or None
            else:
                data["final_grade"] = enrolled_class_grade.final_grade
                data["final_grade_state"] = enrolled_class_grade.final_grade_state
        else:
            data = {
                "prelim_grade": cells[7].value or None,
                "midterm_grade": cells[8].value or None,
                "tentative_final_grade": cells[9].value or None,
                "final_grade": cells[12].value or None,
            }

        if not enrolled_class_grade or (
            enrolled_class_grade
            and enrolled_class_grade.prelim_grade_state
            in models.EnrolledClassGrade.EDITABLE_GRADE_STATES
        ):
            pass

        grade_sheet.rows.create(student=student, status=status, **data)

    grade_sheet.status = models.GradeSheet.Statuses.COMPLETED
    grade_sheet.save()


def grade_sheet_publish(
    *,
    grade_sheet: models.GradeSheet,
    state: models.GradeStates,
    fields: list[str] = None,
):
    if not fields:
        fields = []

    for row in grade_sheet.rows.all():
        enrolled_class = models.EnrolledClass.objects.filter(
            student=row.student, klass=grade_sheet.klass
        ).first()

        if not enrolled_class:
            continue

        enrolled_class_grade, _ = models.EnrolledClassGrade.objects.get_or_create(
            enrolled_class=enrolled_class
        )

        for field in fields:
            grade = getattr(row, field)
            grade_state = getattr(enrolled_class_grade, f"{field}_state")

            if grade and grade_state in models.EnrolledClassGrade.EDITABLE_GRADE_STATES:
                setattr(enrolled_class_grade, field, grade)
                setattr(enrolled_class_grade, f"{field}_state", state)

        enrolled_class_grade.status = row.status
        enrolled_class_grade.save()

    class_grade_state_update(klass=grade_sheet.klass, state=state, fields=fields)


def gwa_sheet_create(*, file: File) -> models.GeneralWeightedAverageSheet:
    gwa_sheet = models.GeneralWeightedAverageSheet.objects.create(file=file)
    gwa_sheet.generate_id()
    tasks.async_gwa_sheet_process.delay(id=gwa_sheet.id)
    return gwa_sheet


def _gwa_sheet_failed(*, gwa_sheet: models.GeneralWeightedAverageSheet, error: str):
    gwa_sheet.status = models.GeneralWeightedAverageSheet.Statuses.FAILED
    gwa_sheet.error_message = error
    gwa_sheet.save()


def gwa_sheet_process(*, gwa_sheet: models.GeneralWeightedAverageSheet) -> None:
    gwa_sheet.status = gwa_sheet.Statuses.PROCESSING
    gwa_sheet.save()

    stats = {
        "success": 0,
        "invalid": 0,
        "total": 0,
    }

    first_row = True

    try:
        file_contents = gwa_sheet.file.read()
        csv_data = file_contents.decode().splitlines()
        reader = csv.reader(csv_data)

        for row in reader:
            if not row:
                continue

            if first_row:
                first_row = False
                continue

            stats["total"] += 1

            data = {
                "id_no": row[0],
                "school_year": row[2],
                "term": row[3],
                "gwa": row[4],
                "pass_percentage": row[5],
                "remark_code": row[7],
                "status": row[6],
            }

            result, err = enrollment_grade_process(data=data)
            if result:
                stats["success"] += 1
            else:
                print(err)
                stats["invalid"] += 1

    except (UnicodeDecodeError, botocore.exceptions.ClientError) as error:
        _gwa_sheet_failed(
            gwa_sheet=gwa_sheet,
            error="Error reading gwa sheet file",
        )
        capture_exception(error)
        return

    gwa_sheet.status = models.GeneralWeightedAverageSheet.Statuses.COMPLETED
    gwa_sheet.success = stats["success"]
    gwa_sheet.invalid = stats["invalid"]
    gwa_sheet.total = stats["total"]
    gwa_sheet.save()


def enrollment_grade_process(*, data: dict) -> tuple:
    """Process Enrollment Grade

    Args:
        data: enrollment grade values
        {
            "id_no":"str",
            "school_year":"str",
            "term":"str",
            "gwa":"str",
            "pass_percentage":"str",
            "remark_code":"str",
            "status":"str",
        }

    """

    sem_mapping = {
        "1": Semesters.FIRST_SEMESTER,
        "2": Semesters.SECOND_SEMESTER,
        "3": Semesters.SUMMER,
    }

    grading_status_mapping = {
        "PASSED": models.EnrollmentGrade.GradingStatuses.PASSED,
        "FAILED": models.EnrollmentGrade.GradingStatuses.FAILED,
    }

    student = models.Student.objects.filter(id_number=data.get("id_no")).first()
    if not student:
        err = f"Invalid Student No: {data.get('id_no')}"
        return False, err

    academic_year = AcademicYear.objects.filter(
        year_start=int(data.get("school_year")[0:4]) - 1,
        year_end=int(data.get("school_year")[0:4]),
    ).first()

    enrollment = models.Enrollment.objects.filter(
        student=student,
        academic_year=academic_year,
        semester__term=sem_mapping.get(data.get("term")),
    ).first()

    if not enrollment:
        err = f"Invalid Enrollment: {data.get('id_no')} SY: {data.get('school_year')}"
        return False, err

    remark_code = None
    if data.get("remark_code"):
        remark_code = RemarkCode.objects.filter(ref_id=data.get("remark_code")).first()

    if not hasattr(enrollment, "grade"):
        models.EnrollmentGrade.objects.create(enrollment=enrollment)

    enrollment.grade.general_weighted_average = (
        data.get("gwa") if data.get("gwa") != "NO GWA" else Decimal(0)
    )
    enrollment.grade.grading_status = grading_status_mapping.get(data.get("status"))
    enrollment.grade.pass_percentage = grading_status_mapping.get(
        data.get("pass_percentage")
    )
    enrollment.grade.remark_code = remark_code
    enrollment.grade.save()

    return True, enrollment


def student_request_review_history_create(
    *, user=User, data: dict
) -> models.StudentRequestReviewHistory:
    return models.StudentRequestReviewHistory.objects.create(user=user, **data)


def _generate_choice_label_mapping(*, choices) -> str:
    choice_mapping = {}
    for item in choices:
        choice_mapping[item.value] = item.label

    return choice_mapping


def change_schedule_request_create(
    *, student: models.Student, data: dict
) -> models.ChangeScheduleRequest:
    data.pop("type")
    request = models.ChangeScheduleRequest.objects.create(student=student, **data)
    status = _generate_choice_label_mapping(
        choices=models.ChangeScheduleRequest.Statuses
    ).get(request.status)
    return request, status


def add_subject_request_create(*, student: models.Student, data: dict) -> tuple:
    data.pop("type")
    request = models.AddSubjectRequest.objects.create(student=student, **data)
    status = _generate_choice_label_mapping(
        choices=models.AddSubjectRequest.Statuses
    ).get(request.status)
    return request, status


def open_class_request_create(*, student: models.Student, data: dict) -> tuple:
    data.pop("type")
    request = models.OpenClassRequest.objects.create(student=student, **data)
    status = _generate_choice_label_mapping(
        choices=models.OpenClassRequest.Statuses
    ).get(request.status)
    return request, status


def withdrawal_request_create(*, student: models.Student, data: dict) -> tuple:
    category = models.WithdrawalRequest.Categories.PARTIAL_WITHDRAWAL
    if data.pop("type") == models.StudentRequestTypes.FULL_WITHDRAWAL:
        category = models.WithdrawalRequest.Categories.FULL_WITHDRAWAL

    request = models.WithdrawalRequest.objects.create(
        student=student, category=category, **data
    )
    status = _generate_choice_label_mapping(
        choices=models.OpenClassRequest.Statuses
    ).get(request.status)
    return request, status


def student_request_create(*, student: models.Student, data: dict) -> dict:
    request_create_method_mapping = {
        models.StudentRequestTypes.CHANGE_SCHEDULE.value: change_schedule_request_create,
        models.StudentRequestTypes.ADD_SUBJECT.value: add_subject_request_create,
        models.StudentRequestTypes.OPEN_CLASS.value: open_class_request_create,
        models.StudentRequestTypes.PARTIAL_WITHDRAWAL.value: withdrawal_request_create,
        models.StudentRequestTypes.FULL_WITHDRAWAL.value: withdrawal_request_create,
    }

    method = request_create_method_mapping.get(data.get("type"))

    if method:
        request, status = method(student=student, data=data)
        request.generate_request_no()

        history_data = {"request": request, "status": status}
        student_request_review_history_create(user=student.user, data=history_data)

        return {"request_no": request.request_no}


def change_schedule_request_update(
    *, request: models.ChangeScheduleRequest, user: User, data: dict
) -> models.ChangeScheduleRequest:
    _data = data.copy()
    remarks = _data.pop("remarks")

    request.__dict__.update(**_data)
    request.save()

    status = _generate_choice_label_mapping(
        choices=models.ChangeScheduleRequest.Statuses
    ).get(request.status)
    history_data = {"request": request, "remarks": remarks, "status": status}
    student_request_review_history_create(user=user, data=history_data)

    event_notif_mapping = {
        models.ChangeScheduleRequest.Statuses.APPROVED: events.REQUEST_CHANGE_SCHEDULE_APPROVED,
        models.ChangeScheduleRequest.Statuses.REJECTED: events.REQUEST_CHANGE_SCHEDULE_REJECTED,
    }

    event = event_notif_mapping.get(request.status)
    if event:
        event_publisher.generic(event, object=request, remarks=remarks)

    return request


def add_subject_request_update(
    *, request: models.AddSubjectRequest, user: User, data: dict
) -> models.AddSubjectRequest:
    _data = data.copy()
    remarks = _data.pop("remarks")

    request.__dict__.update(**_data)
    request.save()

    status = _generate_choice_label_mapping(
        choices=models.AddSubjectRequest.Statuses
    ).get(request.status)
    history_data = {"request": request, "remarks": remarks, "status": status}
    student_request_review_history_create(user=user, data=history_data)

    event_notif_mapping = {
        models.AddSubjectRequest.Statuses.APPROVED: events.REQUEST_ADD_SUBJECT_APPROVED,
        models.AddSubjectRequest.Statuses.REJECTED: events.REQUEST_ADD_SUBJECT_REJECTED,
    }

    event = event_notif_mapping.get(request.status)
    if event:
        event_publisher.generic(event, object=request, remarks=remarks)

    return request


def open_class_request_update(
    *, request: models.OpenClassRequest, user: User, data: dict
) -> models.OpenClassRequest:
    _data = data.copy()
    remarks = _data.pop("remarks")

    prev_status = request.status

    request.__dict__.update(**_data)
    request.save()

    status = _generate_choice_label_mapping(
        choices=models.OpenClassRequest.Statuses
    ).get(request.status)
    history_data = {"request": request, "remarks": remarks, "status": status}
    student_request_review_history_create(user=user, data=history_data)

    for_email_notification = [
        models.OpenClassRequest.Statuses.ENCODED,
        models.OpenClassRequest.Statuses.REJECTED,
        models.OpenClassRequest.Statuses.FOR_APPROVAL,
    ]

    if request.status in for_email_notification:
        event_notif_mapping = {
            models.OpenClassRequest.Statuses.FOR_APPROVAL: events.REQUEST_OPEN_CLASS_FOR_APPROVAL,
            models.OpenClassRequest.Statuses.ENCODED: events.REQUEST_OPEN_CLASS_APPROVED,
            models.OpenClassRequest.Statuses.REJECTED: events.REQUEST_OPEN_CLASS_REJECTED,
        }
        event = event_notif_mapping.get(request.status)

        if (
            prev_status == request.status
            and request.status == models.OpenClassRequest.Statuses.FOR_APPROVAL
        ):
            if not data.get("notify_student", False):
                return request

            event = events.REQUEST_OPEN_CLASS_REVIEW_UPDATED

        if event:
            event_publisher.generic(event, object=request, remarks=remarks)

    return request


def withdrawal_request_update(
    *, request: models.WithdrawalRequest, user: User, data: dict
) -> models.WithdrawalRequest:
    _data = data.copy()
    remarks = _data.pop("remarks")

    prev_status = request.status

    request.__dict__.update(**_data)
    request.save()

    status_choices_mapping = _generate_choice_label_mapping(
        choices=models.WithdrawalRequest.Statuses
    )

    status = status_choices_mapping.get(request.status)
    history_data = {"request": request, "remarks": remarks, "status": status}
    student_request_review_history_create(user=user, data=history_data)

    for_email_notification = [
        models.WithdrawalRequest.Statuses.ENCODED,
        models.WithdrawalRequest.Statuses.REJECTED,
        models.WithdrawalRequest.Statuses.FOR_APPROVAL,
    ]

    if request.status in for_email_notification:
        event_notif_mapping = {
            models.WithdrawalRequest.Statuses.FOR_APPROVAL: events.REQUEST_WITHDRAWAL_FOR_APPROVAL,
            models.WithdrawalRequest.Statuses.ENCODED: events.REQUEST_WITHDRAWAL_APPROVED,
            models.WithdrawalRequest.Statuses.REJECTED: events.REQUEST_WITHDRAWAL_REJECTED,
        }
        event = event_notif_mapping.get(request.status)

        if (
            prev_status == request.status
            and request.status == models.WithdrawalRequest.Statuses.FOR_APPROVAL
        ):
            if not data.get("notify_student", False):
                return request

            event = events.REQUEST_WITHDRAWAL_REVIEW_UPDATED

        if event:
            category_choices_mapping = _generate_choice_label_mapping(
                choices=models.WithdrawalRequest.Categories
            )
            request_type = category_choices_mapping.get(request.category)
            request_description = "Partial Withdrawal request"
            if request.category == models.WithdrawalRequest.Categories.FULL_WITHDRAWAL:
                request_description = "Full Withdrawal request for ALL the subjects enrolled for the current term"

            email_data = {
                "remarks": remarks,
                "request_type": request_type,
                "request_description": request_description,
                "status": status_choices_mapping.get(request.status),
                "prev_status": status_choices_mapping.get(prev_status),
            }
            event_publisher.generic(event, object=request, **email_data)

    return request
