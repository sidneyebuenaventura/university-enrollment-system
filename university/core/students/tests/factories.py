from datetime import date

import factory
import pytest
from factory.django import DjangoModelFactory
from pytest_factoryboy import register

from university.core.accounts.tests.factories import (
    AcademicYearFactory,
    SemesterFactory,
    UserFactory,
)
from university.core.cms.tests.factories import (
    ClassFactory,
    CourseFactory,
    CurriculumFactory,
)
from university.core.students import models
from university.framework.tests import fake, fake_amount


@pytest.fixture
def pre_enrollment(base_enrollment):
    base_enrollment.status = models.Enrollment.Statuses.PRE_ENROLLMENT
    base_enrollment.step = models.Enrollment.Steps.START
    base_enrollment.save()
    return base_enrollment


@pytest.fixture
def enrollment(base_enrollment):
    base_enrollment.status = models.Enrollment.Statuses.ENROLLMENT
    base_enrollment.step = models.Enrollment.Steps.SUBJECTS
    base_enrollment.save()
    return base_enrollment


@register
class StudentFactory(DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    semester = factory.SubFactory(SemesterFactory)
    curriculum = factory.SubFactory(CurriculumFactory)
    course = factory.SubFactory(CourseFactory)
    year_level = factory.LazyFunction(lambda: str(fake.pyint(1, 5)))

    type = models.Student.Types.STUDENT
    status = factory.Iterator(models.Student.Statuses)
    id_number = factory.Sequence(lambda n: f"STUDENT-2022-{n:05d}")

    first_name = factory.LazyFunction(fake.first_name)
    middle_name = factory.LazyFunction(fake.last_name)
    last_name = factory.LazyFunction(fake.last_name)

    birth_date = factory.LazyFunction(fake.date)
    birth_place = factory.LazyFunction(fake.address)
    gender = factory.Iterator(models.Student.Genders)

    civil_status = factory.Iterator(models.Student.CivilStatuses)
    citizenship = factory.Iterator(models.Student.Citizenships)
    nationality = factory.Iterator(models.Student.Nationalities)

    email = factory.LazyFunction(fake.email)
    phone_no = factory.LazyFunction(fake.mobile_number)

    street = factory.LazyFunction(fake.street_address)
    barangay = factory.LazyFunction(fake.province_lgu)
    city = factory.LazyFunction(fake.city)
    province = factory.LazyFunction(fake.province)
    zip_code = factory.LazyFunction(fake.postcode)
    home_phone_no = factory.LazyFunction(fake.mobile_number)

    local_address = factory.LazyFunction(fake.address)
    local_phone_no = factory.LazyFunction(fake.mobile_number)

    guardian_name = factory.LazyFunction(fake.name)
    guardian_address = factory.LazyFunction(fake.address)

    father_name = factory.LazyFunction(fake.name_male)
    father_occupation = factory.LazyFunction(fake.job)
    mother_name = factory.LazyFunction(fake.name_female)
    mother_occupation = factory.LazyFunction(fake.job)

    emergency_contact_name = factory.LazyFunction(fake.name)
    emergency_contact_email = factory.LazyFunction(fake.email)
    emergency_contact_phone_no = factory.LazyFunction(fake.mobile_number)

    class Meta:
        model = models.Student

    @factory.post_generation
    def password_histories(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for password_history in extracted:
                password_history.user = self.user
                password_history.created_at = date.today()
                password_history.save()
        else:
            self.user.password_histories.create(value="password")


@register(_name="base_enrollment")
class EnrollmentFactory(DjangoModelFactory):
    student = factory.SubFactory(StudentFactory)
    academic_year = factory.SubFactory(AcademicYearFactory)
    semester = factory.SubFactory(SemesterFactory)
    year_level = factory.LazyFunction(lambda: str(fake.pyint(1, 5)))

    current_address = factory.LazyFunction(fake.address)
    contact_number = factory.SelfAttribute("student.phone_no")
    personal_email = factory.SelfAttribute("student.user.email")
    institutional_email = factory.SelfAttribute("student.user.email")

    father_name = factory.SelfAttribute("student.father_name")
    father_phone_no = factory.LazyFunction(fake.mobile_number)
    father_email = factory.LazyFunction(fake.email)
    father_occupation = factory.LazyFunction(fake.job)
    mother_occupation = factory.LazyFunction(fake.job)

    mother_name = factory.SelfAttribute("student.mother_name")
    mother_phone_no = factory.LazyFunction(fake.mobile_number)
    mother_email = factory.LazyFunction(fake.email)

    class Meta:
        model = models.Enrollment


@register
class EnrolledClassFactory(DjangoModelFactory):
    enrollment = factory.SubFactory(EnrollmentFactory)

    @factory.lazy_attribute
    def subject_class(self):
        # SubFactory fails due to auto fixtures resulting to a
        # fixture with `class` variable name.
        return ClassFactory()

    class Meta:
        model = models.EnrolledClass


@register
class EnrolledClassGradeFactory(DjangoModelFactory):
    enrolled_class = factory.SubFactory(EnrolledClassFactory)
    grade = factory.LazyFunction(fake_amount)

    class Meta:
        model = models.EnrolledClassGrade


@register
class ChangeScheduleRequestFactory(DjangoModelFactory):
    student = factory.SubFactory(StudentFactory)
    request_no = factory.LazyFunction(lambda: fake.pystr(5, 5).upper())
    detail = factory.LazyFunction(lambda: " ".join(fake.words()).title())
    reason = factory.LazyFunction(lambda: " ".join(fake.words()).title())

    class Meta:
        model = models.ChangeScheduleRequest


@register
class AddSubjectRequestFactory(DjangoModelFactory):
    student = factory.SubFactory(StudentFactory)
    request_no = factory.LazyFunction(lambda: fake.pystr(5, 5).upper())
    detail = factory.LazyFunction(lambda: " ".join(fake.words()).title())
    reason = factory.LazyFunction(lambda: " ".join(fake.words()).title())

    class Meta:
        model = models.AddSubjectRequest


@register
class OpenClassRequestFactory(DjangoModelFactory):
    student = factory.SubFactory(StudentFactory)
    request_no = factory.LazyFunction(lambda: fake.pystr(5, 5).upper())
    detail = factory.LazyFunction(lambda: " ".join(fake.words()).title())
    reason = factory.LazyFunction(lambda: " ".join(fake.words()).title())

    class Meta:
        model = models.OpenClassRequest


@register
class WithdrawalRequestFactory(DjangoModelFactory):
    student = factory.SubFactory(StudentFactory)
    request_no = factory.LazyFunction(lambda: fake.pystr(5, 5).upper())
    detail = factory.LazyFunction(lambda: " ".join(fake.words()).title())
    reason = factory.LazyFunction(lambda: " ".join(fake.words()).title())

    class Meta:
        model = models.WithdrawalRequest
