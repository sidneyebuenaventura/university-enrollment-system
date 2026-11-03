from datetime import date

import factory
from django.contrib.auth import get_user_model
from factory.django import DjangoModelFactory
from pytest_factoryboy import register

from university.core.accounts import models
from university.framework.tests import fake
from university.framework.utils import get_random_string

MODULE_NAMES = [
    "Dashboard",
    "Students",
    "Faculties",
    "SOA",
    "Payments",
    "Accounts",
    "Roles",
]


@register
class UserFactory(DjangoModelFactory):
    username = factory.LazyFunction(lambda: fake.pystr(6, 6).upper())
    first_name = factory.LazyFunction(fake.first_name)
    last_name = factory.LazyFunction(fake.last_name)
    email = factory.LazyFunction(fake.email)
    is_staff = False
    is_first_login = False

    class Meta:
        model = get_user_model()


@register
@register(_name="staff_user")
class StaffUserFactory(DjangoModelFactory):
    username = factory.LazyFunction(lambda: fake.pystr(6, 6).upper())
    first_name = factory.LazyFunction(fake.first_name)
    last_name = factory.LazyFunction(fake.last_name)
    email = factory.LazyFunction(fake.email)
    is_staff = True
    is_first_login = False

    class Meta:
        model = get_user_model()

    @factory.post_generation
    def password_histories(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for password_history in extracted:
                password_history.user = self
                password_history.created_at = date.today()
                password_history.save()
        else:
            self.password_histories.create(value="password")


@register(_name="staff")
class StaffFactory(StaffUserFactory):
    @factory.post_generation
    def departments(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for department in extracted:
                self.departments.add(department)
        else:
            self.departments.add(*[DepartmentFactory() for _ in range(5)])

    @factory.post_generation
    def school_groups(self, create, extracted, **kwargs):
        if not create:
            return

        roles = [RoleFactory() for _ in range(5)]

        for _ in range(3):
            school_group = self.school_groups.create(school=SchoolFactory())
            school_group.roles.add(*roles)

    @factory.post_generation
    def modules(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for module in extracted:
                self.modules.add(module)
        else:
            self.modules.add(*[ModuleFactory() for _ in range(5)])


@register
class RoleFactory(DjangoModelFactory):
    class Meta:
        model = models.Role

    @factory.post_generation
    def role_modules(self, create, extracted, **kwargs):
        if not create:
            return

        modules = [ModuleFactory() for _ in range(5)]

        for module in modules:
            self.rolemodule_set.create(
                module=module,
                has_view_perm=True,
                has_add_perm=True,
                has_change_perm=True,
                has_delete_perm=True,
            )

    @factory.lazy_attribute
    def name(self):
        return f"{fake.job()} - {get_random_string(length=6)}"


@register
class ModuleFactory(DjangoModelFactory):
    platform = models.Module.Platforms.WEB
    name = factory.Iterator(MODULE_NAMES)
    description = factory.LazyFunction(fake.catch_phrase)

    class Meta:
        model = models.Module

    @factory.lazy_attribute
    def codename(self):
        prefixes = {
            models.Module.Platforms.WEB: "web",
            models.Module.Platforms.MOBILE: "mobile",
        }
        return f"{prefixes[self.platform]}.{self.name.lower()}"


@register
class SchoolFactory(DjangoModelFactory):
    name = factory.LazyAttribute(lambda o: f"School of {fake.name()}")
    ref_id = factory.LazyAttribute(lambda o: o.code.lower())

    class Meta:
        model = models.School

    @factory.lazy_attribute
    def code(self):
        words = self.name.split(" ")
        acronym = [word[0] for word in words]
        return "".join(acronym).upper()


@register
class DepartmentFactory(DjangoModelFactory):
    name = factory.LazyAttribute(lambda o: " ".join(fake.words(2)))

    class Meta:
        model = models.Department


@register
class ReligionFactory(DjangoModelFactory):
    code = factory.LazyFunction(lambda: fake.pystr(5, 5).upper())
    description = factory.LazyFunction(fake.text)

    class Meta:
        model = models.Religion


@register
class PersonnelFactory(DjangoModelFactory):
    user = factory.SubFactory(StaffUserFactory, is_staff=True)

    ref_id = factory.LazyFunction(fake.pyint)
    emp_id = factory.Sequence(lambda n: "EMP-2022-%05d" % n)
    old_id = factory.LazyFunction(lambda: fake.pystr(5, 5).upper())

    first_name = factory.LazyFunction(fake.first_name)
    middle_name = factory.LazyFunction(fake.last_name)
    maiden_name = factory.Maybe(
        "is_female", yes_declaration=factory.LazyFunction(fake.last_name)
    )
    last_name = factory.LazyFunction(fake.last_name)

    birth_date = factory.LazyFunction(fake.date)
    birth_place = factory.LazyFunction(fake.address)
    gender = factory.Iterator(models.Personnel.Genders)

    civil_status = factory.Iterator(models.Personnel.CivilStatuses)
    nationality = factory.Iterator(models.Personnel.Nationalities)

    spouse_name = factory.Maybe(
        "is_married", yes_declaration=factory.LazyFunction(fake.name_female)
    )
    spouse_occupation = factory.Maybe(
        "is_married", yes_declaration=factory.LazyFunction(fake.job)
    )
    no_of_child = factory.Maybe(
        "is_married", yes_declaration=factory.LazyFunction(lambda: fake.pyint(1, 5))
    )

    rank = factory.Iterator(models.Personnel.Ranks)
    religion = factory.SubFactory(ReligionFactory)

    sss_no = factory.LazyFunction(fake.sss)
    tin = factory.LazyFunction(fake.ssn)
    license_no = factory.LazyFunction(fake.ssn)
    pagibig_no = factory.LazyFunction(fake.pagibig)
    philhealth_no = factory.LazyFunction(fake.philhealth)

    phone_no = factory.LazyFunction(fake.mobile_number)
    home_phone_no = factory.LazyFunction(fake.mobile_number)
    local_address = factory.LazyFunction(fake.address)
    local_phone_no = factory.LazyFunction(fake.mobile_number)
    street = factory.LazyFunction(fake.street_address)
    barangay = factory.LazyFunction(fake.province_lgu)
    city = factory.LazyFunction(fake.city)
    zip_code = factory.LazyFunction(fake.postcode)

    relative_name = factory.LazyFunction(fake.name)
    relative_relationship = factory.Iterator(["Mother", "Father"])
    relative_address = factory.LazyFunction(fake.address)
    relative_phone_no = factory.LazyFunction(fake.mobile_number)

    union_affiliation = factory.Iterator(models.Personnel.UnionAffiliations)
    employment_type = factory.Iterator(models.Personnel.EmploymentTypes)
    tenure = factory.Iterator(models.Personnel.Tenures)
    employee_status = factory.Iterator(models.Personnel.EmploymentStatuses)
    category = factory.Iterator(models.Personnel.Categories)

    father_name = factory.LazyFunction(fake.name_male)
    mother_name = factory.LazyFunction(fake.name_female)
    marriage_date = factory.Maybe(
        "is_married", yes_declaration=factory.LazyFunction(fake.date)
    )
    employment_date = factory.LazyFunction(fake.date)

    class Meta:
        model = models.Personnel

    class Params:
        is_female = factory.LazyAttribute(
            lambda o: o.gender == models.Personnel.Genders.FEMALE
        )
        is_married = factory.LazyFunction(fake.pybool)


@register(_name="faculty")
class FacultyFactory(PersonnelFactory):
    category = models.Personnel.Categories.FACULTY


@register
class AcademicYearFactory(DjangoModelFactory):
    year_start = factory.LazyFunction(lambda: int(fake.year()))
    year_end = factory.LazyAttribute(lambda o: o.year_start + 1)
    id_start = factory.LazyFunction(lambda: fake.pyint(1000, 2000))
    date_start = factory.LazyFunction(fake.date)
    date_end = factory.LazyFunction(fake.date)

    class Meta:
        model = models.AcademicYear


@register
class SemesterFactory(DjangoModelFactory):
    academic_year = factory.SubFactory(AcademicYearFactory)
    term = factory.Iterator(models.Semester.Terms)
    date_start = factory.LazyFunction(fake.date)
    date_end = factory.LazyFunction(fake.date)
    prelim_date_start = factory.LazyFunction(fake.date)
    prelim_date_end = factory.LazyFunction(fake.date)
    midterm_date_start = factory.LazyFunction(fake.date)
    midterm_date_end = factory.LazyFunction(fake.date)
    final_date_start = factory.LazyFunction(fake.date)
    final_date_end = factory.LazyFunction(fake.date)
    order = factory.LazyFunction(lambda: fake.pyint(1, 3))

    class Meta:
        model = models.Semester


@register
class PasswordHistoryFactory(DjangoModelFactory):
    value = factory.LazyFunction(lambda: fake.pystr(5, 5))
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = models.PasswordHistory
