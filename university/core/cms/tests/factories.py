import factory
from factory.django import DjangoModelFactory
from pytest_factoryboy import register

from university.core.accounts.tests.factories import (
    AcademicYearFactory,
    DepartmentFactory,
    PersonnelFactory,
    SchoolFactory,
)
from university.core.cms import models
from university.core.students.models import Student
from university.framework.tests import fake, fake_amount


@register
class CourseFactory(DjangoModelFactory):
    school = factory.SubFactory(SchoolFactory)

    level = factory.Iterator(models.Course.Levels)
    category = factory.Iterator(models.Course.Categories)

    code = factory.LazyFunction(lambda: fake.pystr(5, 5).upper())
    sub_code = factory.LazyFunction(lambda: fake.pystr(5, 5).upper())
    name = factory.LazyFunction(lambda: " ".join(fake.words()).title())
    major = factory.LazyFunction(lambda: " ".join(fake.words(2)).title())
    minor = factory.LazyFunction(lambda: " ".join(fake.words(2)).title())
    duration = factory.LazyFunction(lambda: str(fake.pyint(3, 6)))
    duration_unit = models.Course.DurationUnits.MONTH
    degree_class = factory.LazyFunction(lambda: " ".join(fake.words(2)).title())
    is_accredited = True
    accredited_year = factory.LazyFunction(fake.year)
    has_board_exam = False
    is_active = True

    class Meta:
        model = models.Course


@register
class CurriculumFactory(DjangoModelFactory):
    course = factory.SubFactory(CourseFactory)

    ref_id = factory.LazyFunction(lambda: str(fake.pyint(1, 4)))
    effective_start_year = factory.LazyFunction(lambda: int(fake.year()))
    effective_end_year = factory.LazyAttribute(lambda o: o.effective_start_year + 1)
    effective_semester = factory.Iterator(models.Semesters)

    is_current = True

    class Meta:
        model = models.Curriculum


@register
class CurriculumPeriodFactory(DjangoModelFactory):
    curriculum = factory.SubFactory(CurriculumFactory)
    semester = factory.Iterator(models.Semesters)
    year_level = factory.LazyFunction(lambda: fake.pyint(1, 4))
    order = factory.LazyFunction(lambda: fake.pyint(1, 4))

    class Meta:
        model = models.CurriculumPeriod


@register
class SubjectGroupingFactory(DjangoModelFactory):
    department = factory.SubFactory(DepartmentFactory)
    ref_id = factory.LazyFunction(fake.pyint)
    name = factory.LazyFunction(lambda: " ".join(fake.words()).title())

    class Meta:
        model = models.SubjectGrouping


@register
class SubjectFactory(DjangoModelFactory):
    school = factory.SubFactory(SchoolFactory)
    grouping = factory.SubFactory(SubjectGroupingFactory)

    ref_id = factory.LazyFunction(fake.pyint)
    charge_code = factory.LazyFunction(lambda: fake.pystr(5, 5).upper())
    course_code = factory.LazyFunction(lambda: fake.pystr(5, 5).upper())
    course_number = factory.LazyFunction(fake.pyint)
    descriptive_code = factory.LazyFunction(lambda: " ".join(fake.words()).title())
    descriptive_title = factory.LazyFunction(lambda: " ".join(fake.words()).title())

    sub_type = factory.Iterator(models.Subject.SubTypes)
    classification = factory.Iterator(models.Subject.Classifications)
    category = factory.Iterator(models.Subject.Categories)

    units = factory.Maybe(
        "is_medicine",
        no_declaration=factory.LazyFunction(
            lambda: fake.pydecimal(
                left_digits=1,
                right_digits=2,
                positive=True,
                min_value=1,
            )
        ),
    )
    no_of_hours = factory.Maybe(
        "is_medicine", yes_declaration=factory.LazyFunction(lambda: fake.pyint(1, 4))
    )
    duration = factory.Iterator(models.Subject.Durations)

    class Meta:
        model = models.Subject

    class Params:
        is_medicine = factory.LazyAttribute(
            lambda o: o.classification == models.Subject.Classifications.MEDICINE
        )


@register
class CurriculumSubjectFactory(DjangoModelFactory):
    curriculum = factory.SubFactory(CurriculumFactory)
    curriculum_period = factory.SubFactory(CurriculumPeriodFactory)
    subject = factory.SubFactory(SubjectFactory)

    subject_class = factory.Iterator(models.CurriculumSubject.SubjectClasses)
    category_rate = factory.Iterator(models.CurriculumSubject.CategoryRates)

    lec_hrs = factory.LazyFunction(lambda: fake.pyint(1, 6))
    lab_wk = factory.LazyFunction(lambda: fake.pyint(1, 3))
    order = factory.LazyFunction(lambda: fake.pyint(1, 20))

    class Meta:
        model = models.CurriculumSubject


@register
class CurriculumSubjectRequisiteFactory(DjangoModelFactory):
    curriculum_subject = factory.SubFactory(CurriculumSubjectFactory)
    requisite_subject = factory.SubFactory(CurriculumSubjectFactory)
    type = factory.Iterator(models.CurriculumSubjectRequisite.Types)

    class Meta:
        model = models.CurriculumSubjectRequisite


@register(_name="klass")
class ClassFactory(DjangoModelFactory):
    subject = factory.SubFactory(SubjectFactory)
    instructor = factory.SubFactory(PersonnelFactory)

    class_code = factory.LazyFunction(lambda: fake.pystr(5, 5).upper())
    class_size = factory.LazyFunction(lambda: fake.pyint(20, 50))

    class Meta:
        model = models.Class


@register
class ClassificationFactory(DjangoModelFactory):
    ref_id = factory.LazyFunction(fake.pyint)
    name = factory.LazyFunction(lambda: " ".join(fake.words()).title())

    class Meta:
        model = models.Classification


@register
class BuildingFactory(DjangoModelFactory):
    ref_id = factory.LazyFunction(lambda: str(fake.pyint(1, 10)))
    sub_code = factory.LazyFunction(lambda: fake.pystr(5, 5).upper())
    no_of_floors = factory.LazyFunction(lambda: int(fake.floor_number()))
    name = factory.LazyFunction(fake.building_name)
    campus = factory.LazyFunction(fake.building_name)
    notes = factory.LazyFunction(fake.building_name)

    class Meta:
        model = models.Building
        skip_postgeneration_save = True

    @factory.post_generation
    def schools(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for school in extracted:
                self.schools.add(school)
        else:
            self.schools.add(*[SchoolFactory() for _ in range(5)])


@register
class RoomFactory(DjangoModelFactory):
    school = factory.SubFactory(SchoolFactory)
    classification = factory.SubFactory(ClassificationFactory)
    building = factory.SubFactory(BuildingFactory)

    number = factory.LazyFunction(fake.floor_unit_number)
    name = factory.LazyFunction(fake.building_number)
    size = factory.LazyFunction(lambda: f"{fake.pyint(4, 8)}x{fake.pyint(4, 8)}")
    floor_no = factory.LazyFunction(lambda: int(fake.floor_number()))
    wing = factory.Iterator(["North", "East", "South", "West"])
    capacity = factory.LazyFunction(lambda: fake.pyint(20, 40))
    furniture = factory.LazyFunction(lambda: str(fake.pyint(20, 40)))

    class Meta:
        model = models.Room


@register(_name="class_schedule")
class ClassScheduleFactory(DjangoModelFactory):
    room = factory.SubFactory(RoomFactory)

    ref_id = factory.LazyFunction(fake.pyint)
    time_in = factory.LazyFunction(fake.time)
    time_out = factory.LazyFunction(fake.time)
    day = factory.Iterator(models.ClassSchedule.Days)

    class Meta:
        model = models.ClassSchedule

    @factory.lazy_attribute
    def klass(self):
        # SubFactory fails due to auto fixtures resulting to a
        # fixture with `class` variable name.
        return ClassFactory()


@register
class FeeFactory(DjangoModelFactory):
    academic_year = factory.SubFactory(AcademicYearFactory)

    code = factory.LazyFunction(lambda: fake.pystr(5, 5).upper())
    name = factory.LazyFunction(lambda: " ".join(fake.words()).title())
    type = factory.Iterator(models.Fee.Types)
    description = factory.LazyFunction(lambda: fake.pystr(20, 50).upper())
    remarks = factory.LazyFunction(lambda: fake.pystr(20, 50).upper())
    amount = factory.LazyFunction(fake_amount)

    class Meta:
        model = models.Fee


@register
class FeeSpecificationFactory(DjangoModelFactory):
    school = factory.SubFactory(SchoolFactory)
    subject = factory.SubFactory(SubjectFactory)
    academic_year = factory.SubFactory(AcademicYearFactory)

    code = factory.LazyFunction(lambda: fake.pystr(5, 5).upper())

    semester_from = factory.Iterator(models.Semesters)
    semester_to = factory.Iterator(models.Semesters)

    year_level_from = factory.LazyFunction(lambda: fake.pyint(1, 4))
    year_level_to = factory.LazyAttribute(lambda o: fake.pyint(o.year_level_from, 4))

    class Meta:
        model = models.FeeSpecification
        skip_postgeneration_save = True

    @factory.post_generation
    def fees(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for fee in extracted:
                self.fees.add(fee)
        else:
            self.fees.add(*[FeeFactory() for _ in range(5)])


class MiscellaneousFeeSpecificationFactory(FeeSpecificationFactory):
    total_unit_from = 0
    total_unit_to = factory.LazyFunction(lambda: fake.pyint(1, 4))

    class Meta:
        model = models.MiscellaneousFeeSpecification


class OtherFeeSpecificationFactory(FeeSpecificationFactory):
    subject_group = factory.SubFactory(SubjectGroupingFactory)
    student_type = factory.Iterator(Student.Types)
    course_category = factory.Iterator(models.Course.Categories)

    class Meta:
        model = models.OtherFeeSpecification


@register
class DiscountFactory(DjangoModelFactory):
    department = factory.SubFactory(DepartmentFactory)

    type = factory.Iterator(models.Discount.Types)
    apply_to = ["TF", "LF"]

    ref_id = factory.LazyFunction(lambda: str(fake.pyint(1, 50)))
    name = factory.LazyFunction(lambda: fake.pystr(5, 5).upper())
    percentage = factory.LazyFunction(
        lambda: fake.pydecimal(
            left_digits=1,
            right_digits=2,
            positive=True,
            min_value=1,
        )
    )
    remarks = factory.LazyFunction(lambda: fake.pystr(20, 50).upper())
    category_rate_exemption = ["ITR", "NR"]

    class Meta:
        model = models.Discount
        skip_postgeneration_save = True

    @factory.post_generation
    def fee_exemptions(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for fee in extracted:
                self.fee_exemptions.add(fee)
        else:
            self.fee_exemptions.add(*[FeeFactory() for _ in range(5)])
