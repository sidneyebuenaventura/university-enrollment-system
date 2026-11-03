from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import exceptions

from university.core.accounts.selectors import current_semester_get, next_semester_get
from university.core.cms.models import (
    Class,
    Course,
    CurriculumSubject,
)
from university.core.cms.selectors import class_tuition_fee_get, subject_has_class
from university.payment.models import BukasTransaction, StatementOfAccount

from .models import EnrolledClass, EnrolledClassGrade, Enrollment, Student

User = get_user_model()


def enrollment_get_ongoing(
    *, user: User, raise_exception: bool = False
) -> list[Enrollment]:
    obj = (
        Enrollment.objects.select_related(
            "statement_of_account",
        )
        .prefetch_related(
            "enrolled_classes",
            "enrolled_classes__klass",
            "enrolled_classes__klass__subject",
            "enrolled_classes__klass__class_schedules",
            "enrolled_classes__klass__class_schedules__room",
            "discounts",
        )
        .filter(
            student__user=user,
            status__in=Enrollment.ONGOING_STATUSES + [Enrollment.Statuses.PRE_ENROLLED],
        )
        .order_by("-year_level", "-semester__order")
        .first()
    )
    if not obj and raise_exception:
        raise exceptions.NotFound("No ongoing enrollment.")
    return obj


def enrollment_get_active(
    *, user: User, raise_exception: bool = False
) -> list[Enrollment]:
    """Retrieves enrollment for the current Academic year and semester"""
    current_semester = current_semester_get()
    obj = (
        Enrollment.objects.select_related(
            "statement_of_account",
        )
        .prefetch_related(
            "enrolled_classes",
            "enrolled_classes__klass",
            "enrolled_classes__klass__subject",
            "enrolled_classes__klass__class_schedules",
            "enrolled_classes__klass__class_schedules__room",
            "discounts",
        )
        .filter(
            student__user=user,
            semester=current_semester,
        )
        .order_by("-year_level", "-semester__order")
        .first()
    )
    if not obj and raise_exception:
        raise exceptions.NotFound("No ongoing enrollment.")
    return obj


def enrollment_get_latest_enrolled(
    *, user: User, raise_exception: bool = False
) -> Enrollment:
    """Retrieve latest enrollment with Enrolled status"""
    obj = (
        Enrollment.objects.select_related(
            "statement_of_account",
        )
        .prefetch_related(
            "enrolled_classes",
            "enrolled_classes__klass",
            "enrolled_classes__klass__subject",
            "enrolled_classes__klass__class_schedules",
            "enrolled_classes__klass__class_schedules__room",
            "discounts",
        )
        .filter(student__user=user, status=Enrollment.Statuses.ENROLLED)
        .order_by("-created_at")
        .first()
    )
    if not obj and raise_exception:
        raise exceptions.NotFound("No ongoing enrollment.")
    return obj


def enrollment_get_for_payment(
    *, user: User, raise_exception: bool = False
) -> Enrollment:
    obj = (
        Enrollment.objects.filter(
            student__user=user, status=Enrollment.Statuses.ENROLLMENT
        )
        .order_by("-year_level", "-semester__order")
        .first()
    )
    if not obj and raise_exception:
        raise exceptions.NotFound("No enrollment for payment.")
    return obj


def enrollment_get_latest(*, user: User, raise_exception: bool = False) -> Enrollment:
    obj = (
        Enrollment.objects.filter(student__user=user)
        .order_by("-academic_year__year_start", "-year_level", "-semester__order")
        .first()
    )
    if not obj and raise_exception:
        raise exceptions.NotFound("No enrollment record found.")
    return obj


def enrollment_curriculum_subject_is_completed(
    *, enrollment: Enrollment, curriculum_subject: CurriculumSubject
) -> bool:
    enrolled_class = (
        enrollment.enrolled_classes.filter(klass__subject=curriculum_subject.subject)
        .select_related("grades")
        .first()
    )

    if not enrolled_class:
        return False

    if not hasattr(enrolled_class, "grades"):
        return False

    return enrolled_class.grades.status == EnrolledClassGrade.Statuses.PASSED


def enrollment_total_units_get(*, enrollment: Enrollment) -> int:
    units = 0

    for enrolled_class in enrollment.enrolled_classes.all():
        if enrolled_class.klass.subject:
            units += enrolled_class.klass.subject.units

    return units


def student_course_get(*, user: User) -> Course:
    return user.student.course


def student_enrollment_passed_units_get(*, enrollment: Enrollment) -> int:
    enrolled_classes = enrollment.enrolled_classes.all()
    units = 0

    for enrolled_class in enrolled_classes:
        if hasattr(enrolled_class, "grades"):
            if enrolled_class.grades.status == EnrolledClassGrade.Statuses.PASSED:
                if enrolled_class.klass.subject:
                    units += enrolled_class.klass.subject.units

    return units


def student_enrollment_failed_units_get(*, enrollment: Enrollment) -> int:
    enrolled_classes = enrollment.enrolled_classes.all()
    units = 0

    for enrolled_class in enrolled_classes:
        if hasattr(enrolled_class, "grades"):
            if enrolled_class.grades.status == EnrolledClassGrade.Statuses.FAILED:
                if enrolled_class.klass.subject:
                    units += enrolled_class.klass.subject.units

    return units


def student_class_list(*, user: User) -> list[Class]:
    enrollment = enrollment_get_active(user=user)
    classes = Class.objects.none()

    if enrollment:
        classes = Class.objects.filter(
            enrollments__enrollment=enrollment,
            enrollments__status=EnrolledClass.Statuses.ENROLLED,
        )

    return classes


def enrollment_tuition_fee_compute(*, enrollment: Enrollment) -> Decimal:
    enrolled_classes = enrollment.enrolled_classes.filter(
        status=EnrolledClass.Statuses.APPROVED
    )
    tuition_fee = 0
    for klass in enrolled_classes:
        tuition_fee += class_tuition_fee_get(
            year_start=enrollment.year_start, year_end=enrollment.year_end, klass=klass
        )
    return


def enrollment_bukas_transaction_get(*, soa: StatementOfAccount) -> BukasTransaction:
    bukas_transaction = (
        BukasTransaction.objects.select_for_update()
        .filter(soa=soa)
        .order_by("-created_at")
        .first()
    )
    return bukas_transaction


def student_has_failed_subject_get(*, student: Student) -> bool:
    latest_enrollment = enrollment_get_latest_enrolled(user=student.user)
    if hasattr(latest_enrollment, "grading_status"):
        return latest_enrollment.grading_status == Enrollment.GradingStatuses.FAILED
    return False


def student_has_remaining_balance_get(*, user: User) -> bool:
    latest_enrollment = enrollment_get_latest_enrolled(user=user)
    return latest_enrollment.statement_of_account.get_remaining_balance() > 0


def next_semester_enrollment_list() -> list[Enrollment]:
    next_semester = next_semester_get()
    enrollments = Enrollment.objects.none

    if next_semester:
        enrollments = (
            next_semester.enrollments.all()
            .select_related("student")
            .prefetch_related(
                "student__course",
                "student__course__school",
            )
        )
        return enrollments
    else:
        raise exceptions.NotFound(
            "No semester configuration or pre-enrollments yet for the next semester."
        )


def enrollment_get_upcoming(*, user: User, raise_exception: bool = False) -> Enrollment:
    upcoming_semester = next_semester_get()
    obj = Enrollment.objects.filter(
        student__user=user, semester=upcoming_semester
    ).first()
    if not obj and raise_exception:
        raise exceptions.NotFound("No enrollment record found.")
    return obj


def enrollment_latest_enrolled_total_units_get(*, user: User):
    latest_enrolled = enrollment_get_latest_enrolled(user=user)
    units = 0
    if hasattr(latest_enrolled, "enrolled_classes"):
        for enrolled_class in latest_enrolled.enrolled_classes.all():
            if enrolled_class.klass.subject:
                units += enrolled_class.klass.subject.units

    return units


def enrollment_subjects_list(
    *, student: Student, passed_curr_subj_ids=list[int]
) -> list[CurriculumSubject]:
    """
    List all curriculum subjects that the authenticated can
    select for current enrollment
    """
    curriculum_subjects = student.curriculum.subjects.all()
    next_semester = next_semester_get()

    curr_subj_ids = []
    for curr_subj in curriculum_subjects.exclude(id__in=passed_curr_subj_ids):
        has_class = subject_has_class(subject=curr_subj.subject, semester=next_semester)

        if not has_class:
            continue

        curr_subj_ids.append(curr_subj.id)

    return CurriculumSubject.objects.filter(id__in=curr_subj_ids)
