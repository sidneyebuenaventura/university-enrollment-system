from decimal import Decimal

from django.db.models import Q

from university.core.accounts.models import AcademicYear, Semester
from university.core.students.models import Student

from .models import (
    Class,
    Course,
    CurriculumPeriod,
    CurriculumSubject,
    Fee,
    LaboratoryFee,
    MiscellaneousFeeSpecification,
    OtherFeeSpecification,
    Semesters,
    Subject,
    SubjectGrouping,
)

FEE_SEMESTER_QUERIES = {
    Semesters.FIRST_SEMESTER: Q(
        Q(semester_from=Semesters.FIRST_SEMESTER)
        | Q(semester_to=Semesters.FIRST_SEMESTER)
    ),
    Semesters.SECOND_SEMESTER: Q(
        Q(semester_from=Semesters.SECOND_SEMESTER)
        | Q(semester_to=Semesters.SECOND_SEMESTER)
        | Q(semester_from=Semesters.FIRST_SEMESTER, semester_to=Semesters.SUMMER)
    ),
    Semesters.SUMMER: Q(
        Q(semester_from=Semesters.SUMMER) | Q(semester_to=Semesters.SUMMER)
    ),
}


def miscellaneous_fees_get(
    *,
    academic_year: AcademicYear,
    curriculum_period: CurriculumPeriod,
    total_units: int,
):
    specs = MiscellaneousFeeSpecification.objects.filter(
        Q(
            academic_year=academic_year,
            year_level_to__lte=curriculum_period.year_level,
            year_level_from__gte=curriculum_period.year_level,
        )
        & Q(
            Q(
                total_unit_to=0,
                total_unit_from=0,
            )
            | Q(
                total_unit_to__lte=total_units,
                total_unit_from__gte=total_units,
            )
        )
        & FEE_SEMESTER_QUERIES.get(curriculum_period.semester)
    ).order_by("-total_unit_to", "-total_unit_from")
    spec = specs.first()

    if spec:
        return spec.fees.all()

    return Fee.objects.none()


def other_fees_get(
    *,
    academic_year: AcademicYear,
    curriculum_period: CurriculumPeriod,
    subject_group: SubjectGrouping,
    student: Student,
    course: Course,
):
    specs = OtherFeeSpecification.objects.filter(
        Q(
            academic_year=academic_year,
            year_level_to__lte=curriculum_period.year_level,
            year_level_from__gte=curriculum_period.year_level,
        )
        & Q(
            Q(
                subject_group__isnull=True,
            )
            | Q(
                subject_group=subject_group,
            )
        )
        & Q(
            Q(
                student_type__isnull=True,
            )
            | Q(
                student_type=student.type,
            )
        )
        & Q(
            Q(
                course_category__isnull=True,
            )
            | Q(
                course_category=course.category,
            )
        )
        & FEE_SEMESTER_QUERIES.get(curriculum_period.semester)
    ).order_by("-subject_group", "-student_type", "-course_category")
    spec = specs.first()

    if spec:
        return spec.fees.all()

    return Fee.objects.none()


def laboratory_fee_get(*, academic_year: AcademicYear, subject: Subject):
    return LaboratoryFee.objects.filter(
        academic_year=academic_year, subject=subject
    ).first()


def subject_tuition_fee_compute(
    *, year_start: int, year_end: int, curriculum_subject: CurriculumSubject
) -> Decimal:
    total_fee = 0
    subject = curriculum_subject.subject

    rate = 0
    if curriculum_subject.tuition_fee_category:
        tuition_fee_rate = (
            curriculum_subject.tuition_fee_category.tuition_fee_category_rates.filter(
                year_start=year_start, year_end=year_end
            ).first()
        )
        if tuition_fee_rate:
            rate = tuition_fee_rate.rate

    if curriculum_subject.subject.classification == Subject.Classifications.MEDICINE:
        total_fee = rate
    else:
        total_fee = rate * subject.units

    return total_fee


def class_tuition_fee_get(*, year_start: int, year_end: int, klass: Class) -> Decimal:
    return subject_tuition_fee_compute(
        year_start=year_start,
        year_end=year_end,
        curriculum_subject=klass.curriculum_subject,
    )


def subject_has_class(*, subject: Subject, semester: Semester) -> bool:
    return (
        Class.objects.filter(
            subject=subject, semester=semester, is_dissolved=False
        ).count()
        > 0
    )
