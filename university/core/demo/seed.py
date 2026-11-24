"""Builds the demo data for the seed_demo command.

Dates are worked out from the day it runs. The first semester of the current
school year is always halfway through and enrollment for the second semester
is open, so there's something to click through whenever the demo is seeded.

Everything goes through the models and soa_create directly. Nothing here
publishes events, so no emails go out while seeding.
"""

import itertools
import random
from datetime import datetime, time, timedelta
from decimal import Decimal
from io import StringIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.utils import timezone
from django.utils.text import slugify
from faker import Faker

from university.core import events
from university.core.accounts.constants import MobileModule, ReservedRole
from university.core.accounts.models import (
    AcademicYear,
    Department,
    Module,
    Personnel,
    Role,
    School,
    Semester,
    UserSchoolGroup,
)
from university.core.cms.models import (
    Announcement,
    Building,
    Class,
    Classification,
    ClassSchedule,
    Course,
    Curriculum,
    CurriculumPeriod,
    CurriculumSubject,
    CurriculumSubjectRequisite,
    Discount,
    Fee,
    LaboratoryFee,
    MiscellaneousFeeSpecification,
    OtherFeeSpecification,
    Room,
    Subject,
    SubjectGrouping,
    TuitionFeeCategory,
    TuitionFeeRate,
)
from university.core.maintenance.models import EnrollmentSchedule, ModuleConfiguration
from university.core.maintenance.services import enrollment_start
from university.core.students.models import (
    EnrolledClass,
    EnrolledClassGrade,
    Enrollment,
    EnrollmentDiscount,
    EnrollmentEvent,
    EnrollmentGrade,
    EnrollmentStatus,
    GradeStates,
    Student,
)
from university.payment.models import (
    AccountTransaction,
    CashierTransaction,
    OverTheCounterTransaction,
)
from university.payment.services import soa_create

from . import data

User = get_user_model()

DEMO_PASSWORD = "demo1234"
ADMIN_USERNAME = "admin"
STUDENT_USERNAME = "student"
EMAIL_DOMAIN = "university.test"

INIT_COMMANDS = [
    "initialize_modules",
    "initialize_module_permissions",
    "initialize_reserved_roles",
    "initialize_superuser_role",
    "initialize_module_configurations",
    "initialize_dragonpay_channels",
]

FS = Semester.Terms.FIRST_SEMESTER
SS = Semester.Terms.SECOND_SEMESTER
SUMMER = Semester.Terms.SUMMER

LAB_CATEGORIES = {
    "CS": Subject.LabCategories.COMPUTER,
    "ACC": Subject.LabCategories.ACCOUNTING,
}


def money(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"))


def at(day, hour=9):
    return timezone.make_aware(datetime.combine(day, time(hour)))


def backdate(obj, when):
    type(obj).objects.filter(pk=obj.pk).update(created_at=when)


def receipt_pdf(bank, reference, amount, when) -> bytes:
    """A one-page PDF standing in for a student's transfer receipt"""
    lines = [
        "Fund Transfer Receipt",
        f"Bank: {bank}",
        f"Reference: {reference}",
        f"Amount: PHP {amount:,.2f}",
        f"Date: {timezone.localtime(when):%Y-%m-%d %H:%M}",
    ]
    text = " 0 -20 Td ".join(f"({line}) Tj" for line in lines)
    stream = f"BT /F1 12 Tf 30 160 Td {text} ET".encode()

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    pdf = b"%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += b"%d 0 obj\n%s\nendobj\n" % (number, body)

    xref = len(pdf)
    pdf += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    pdf += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    pdf += b"trailer\n<< /Size %d /Root 1 0 R >>\n" % (len(objects) + 1)
    pdf += b"startxref\n%d\n%%%%EOF\n" % xref
    return pdf


class DemoSeeder:
    def __init__(self, *, students: int = 40, seed: int = 42, today=None):
        self.student_count = students
        self.rng = random.Random(seed)
        self.fake = Faker("en_PH")
        self.fake.seed_instance(seed)
        self.today = today or timezone.localdate()
        self.now = timezone.now()
        self.password = make_password(DEMO_PASSWORD)

        self.years = []
        self.semesters = {}
        self.schools = {}
        self.departments = {}
        self.groupings = {}
        self.faculty = {}
        self.subjects = {}
        self.subject_departments = {}
        self.courses = {}
        self.periods = {}
        self.lecture_rooms = []
        self.lab_rooms = []
        self.tuition_categories = {}
        self.tuition_rates = {}
        self.fee_specs = {}
        self.discounts = {}
        self.classes = {}
        self.room_usage = set()
        self.block_usage = set()
        self.next_semester_plans = []

        self.employee_ids = itertools.count(1001)
        self.class_codes = itertools.count(1001)
        self.receipt_numbers = itertools.count(1)

    def run(self):
        for command in INIT_COMMANDS:
            call_command(command, stdout=StringIO())

        self.create_calendar()
        self.create_organization()
        self.create_admin()
        self.create_catalogue()
        self.create_fees()
        self.create_students()
        self.open_enrollment()
        self.create_announcements()

    @property
    def current_year(self):
        return self.years[-1]

    # Calendar

    def create_calendar(self):
        first_semester_start = self.today - timedelta(days=60)
        year_start = first_semester_start.year
        if first_semester_start.month < 6:
            year_start -= 1

        # Three past school years for the older students' records
        for offset in range(3, -1, -1):
            start = first_semester_start - timedelta(weeks=52 * offset)
            self._create_school_year(year_start - offset, start)

    def _create_school_year(self, year_start, first_semester_start):
        first_end = first_semester_start + timedelta(days=120)
        second_start = first_end + timedelta(days=21)
        second_end = second_start + timedelta(days=120)
        summer_start = second_end + timedelta(days=14)
        summer_end = summer_start + timedelta(days=42)

        year = AcademicYear.objects.create(
            year_start=year_start,
            year_end=year_start + 1,
            date_start=first_semester_start,
            date_end=summer_end,
            id_start=1,
        )
        self.years.append(year)

        terms = [
            (FS, first_semester_start, first_end),
            (SS, second_start, second_end),
            (SUMMER, summer_start, summer_end),
        ]
        for order, (term, start, end) in enumerate(terms, start=1):
            length = (end - start).days
            prelim = start + timedelta(days=length * 3 // 10)
            midterm = start + timedelta(days=length * 6 // 10)
            final = end - timedelta(days=7)

            self.semesters[(year.id, term)] = Semester.objects.create(
                academic_year=year,
                term=term,
                order=order,
                date_start=start,
                date_end=end,
                prelim_date_start=prelim,
                prelim_date_end=prelim + timedelta(days=4),
                midterm_date_start=midterm,
                midterm_date_end=midterm + timedelta(days=4),
                final_date_start=final,
                final_date_end=end,
            )

    # Schools, departments, faculty and rooms

    def create_organization(self):
        for school in data.SCHOOLS:
            self.schools[school["code"]] = School.objects.create(
                ref_id=school["code"].lower(), **school
            )

        for department in data.DEPARTMENTS:
            school = self.schools.get(department["school"])
            self.departments[department["code"]] = Department.objects.create(
                school=school,
                ref_id=department["code"].lower(),
                code=department["code"],
                name=department["name"],
            )

        faculty_counts = {"CS": 4, "ACC": 4, "GE": 4, "PE": 2}
        for code, count in faculty_counts.items():
            department = self.departments[code]
            members = [
                self._personnel(Personnel.Categories.FACULTY) for _ in range(count)
            ]
            department.users.add(*[member.user for member in members])
            department.department_head = members[0]
            department.save()
            self.faculty[code] = members

            if department.school:
                department.school.dean = members[0].user
                department.school.save()

        lecture = Classification.objects.create(ref_id="1", name="Lecture Room")
        laboratory = Classification.objects.create(ref_id="2", name="Laboratory")

        for building_data in data.BUILDINGS:
            school = self.schools[building_data["school"]]
            building = Building.objects.create(
                ref_id=building_data["prefix"],
                sub_code=building_data["prefix"],
                name=building_data["name"],
                no_of_floors=building_data["floors"],
                campus="Main",
            )
            building.schools.add(school)

            for floor in range(1, building_data["floors"] + 1):
                for number in range(1, 5):
                    is_lab = number == 4
                    room = Room.objects.create(
                        school=school,
                        building=building,
                        classification=laboratory if is_lab else lecture,
                        number=f"{building_data['prefix']}{floor}0{number}",
                        floor_no=floor,
                        capacity=40,
                        is_lecture_room=not is_lab,
                    )
                    (self.lab_rooms if is_lab else self.lecture_rooms).append(room)

    def _personnel(self, category, user=None):
        gender = self.rng.choice(Personnel.Genders.values)
        first_name, last_name = self._name(gender)
        emp_id = f"EMP-{next(self.employee_ids)}"

        if not user:
            user = User(
                username=emp_id.lower(),
                first_name=first_name,
                last_name=last_name,
                email=f"{emp_id.lower()}@{EMAIL_DOMAIN}",
                is_staff=True,
                is_first_login=False,
            )
            user.set_unusable_password()
            user.save()

        return Personnel.objects.create(
            user=user,
            emp_id=emp_id,
            first_name=user.first_name,
            last_name=user.last_name,
            gender=gender,
            category=category,
            employment_type=Personnel.EmploymentTypes.FULL_TIME,
            tenure=Personnel.Tenures.REGULAR,
            phone_no=self.fake.mobile_number(),
        )

    def _name(self, gender):
        first_names = data.MALE_FIRST_NAMES
        if gender == "F":
            first_names = data.FEMALE_FIRST_NAMES
        return self.rng.choice(first_names), self.rng.choice(data.LAST_NAMES)

    def create_admin(self):
        user = User.objects.create(
            username=ADMIN_USERNAME,
            first_name="Demo",
            last_name="Admin",
            email=f"{ADMIN_USERNAME}@{EMAIL_DOMAIN}",
            password=self.password,
            is_staff=True,
            is_superuser=True,
            is_first_login=False,
        )
        user.password_histories.create(value=self.password)
        self._personnel(Personnel.Categories.ADMIN_EMPLOYEE, user=user)

        role = Role.objects.get(name=ReservedRole.SUPER_ADMIN)
        user.groups.add(role)
        for school in self.schools.values():
            group = UserSchoolGroup.objects.create(school=school, user=user)
            group.roles.add(role)

        user.modules.add(*Module.objects.filter(platform=Module.Platforms.WEB))
        self.admin = user

    # Subjects, courses and curricula

    def create_catalogue(self):
        for code, department in self.departments.items():
            self.groupings[code] = SubjectGrouping.objects.create(
                department=department,
                ref_id=code,
                name=department.name,
                is_gen_ed=code in ("GE", "PE"),
            )

        for code, (title, units, department) in data.GENERAL_EDUCATION.items():
            self._subject(code, title, units, department, professional=False)

        first_year = self.years[0]

        for course_data in data.COURSES:
            code = course_data["code"]
            school = self.schools[course_data["school"]]
            course = Course.objects.create(
                school=school,
                level=Course.Levels.BACHELOR_DEGREE,
                category=course_data["category"],
                code=code,
                sub_code=code,
                name=course_data["name"],
                duration="4",
                duration_unit=Course.DurationUnits.YEAR,
                has_board_exam=code == "BSA",
            )
            curriculum = Curriculum.objects.create(
                course=course,
                ref_id=f"{code}-{first_year.year_start}",
                effective_start_year=first_year.year_start,
                effective_end_year=first_year.year_start + 4,
                is_current=True,
            )
            self.courses[code] = course

            curriculum_subjects = {}
            periods = course_data["curriculum"].items()

            for order, ((year_level, term), entries) in enumerate(periods, start=1):
                period = CurriculumPeriod.objects.create(
                    curriculum=curriculum,
                    semester=term,
                    year_level=year_level,
                    order=order,
                )
                self.periods[(code, year_level, term)] = period

                for position, entry in enumerate(entries, start=1):
                    if isinstance(entry, str):
                        subject = self.subjects[entry]
                    else:
                        subject_code, title, units, has_lab = entry
                        subject = self._subject(
                            subject_code,
                            title,
                            units,
                            course_data["department"],
                            professional=True,
                            has_lab=has_lab,
                            school=school,
                        )

                    professional = subject.is_professional_subject
                    rates = CurriculumSubject.CategoryRates
                    curriculum_subjects[subject.course_code] = (
                        CurriculumSubject.objects.create(
                            curriculum=curriculum,
                            curriculum_period=period,
                            subject=subject,
                            subject_class=(
                                CurriculumSubject.SubjectClasses.MAJOR
                                if professional
                                else None
                            ),
                            category_rate=(
                                rates.PROFESSIONAL_EDUCATION
                                if professional
                                else rates.NON_PROFESSIONAL
                            ),
                            lec_hrs=int(subject.units),
                            lab_wk=1 if subject.is_lab_subject else 0,
                            order=position,
                        )
                    )

            for subject_code, requisites in data.PREREQUISITES.items():
                if subject_code not in curriculum_subjects:
                    continue

                for requisite in requisites:
                    CurriculumSubjectRequisite.objects.create(
                        curriculum_subject=curriculum_subjects[subject_code],
                        requisite_subject=curriculum_subjects[requisite],
                    )

    def _subject(
        self,
        code,
        title,
        units,
        department,
        *,
        professional,
        has_lab=False,
        school=None,
    ):
        classification = Subject.Classifications.NONE
        if code.startswith("PE"):
            classification = Subject.Classifications.PE
        elif code.startswith("NSTP"):
            classification = Subject.Classifications.N

        subject = Subject.objects.create(
            school=school,
            grouping=self.groupings[department],
            ref_id=code,
            charge_code=code,
            course_code=code,
            descriptive_code=code,
            descriptive_title=title,
            is_professional_subject=professional,
            is_lab_subject=has_lab,
            lab_category=LAB_CATEGORIES.get(department) if has_lab else None,
            classification=classification,
            category=(
                Subject.Categories.LABORATORY if has_lab else Subject.Categories.LECTURE
            ),
            units=Decimal(units),
            duration=Subject.Durations.SEMESTRAL,
        )
        self.subjects[code] = subject
        self.subject_departments[code] = department
        return subject

    # Tuition, fees and discounts

    def create_fees(self):
        categories = {
            "professional": TuitionFeeCategory.Categories.PROFESSIONAL,
            "general": TuitionFeeCategory.Categories.NONPRO,
        }
        for kind, category in categories.items():
            for year_level in range(1, 5):
                self.tuition_categories[(kind, year_level)] = (
                    TuitionFeeCategory.objects.create(
                        ref_id=f"{category}-{year_level}",
                        year_level=year_level,
                        category=category,
                    )
                )

        for age, year in enumerate(reversed(self.years)):
            factor = (1 - data.YEARLY_TUITION_INCREASE) ** age

            for (kind, year_level), category in self.tuition_categories.items():
                self.tuition_rates[(year.id, kind, year_level)] = (
                    TuitionFeeRate.objects.create(
                        tuition_fee_category=category,
                        academic_year=year,
                        rate=money(data.TUITION_PER_UNIT[kind] * factor),
                    )
                )

            fee_years = {
                "academic_year": year,
                "semester_from": FS,
                "semester_to": SS,
                "year_level_from": 1,
                "year_level_to": 4,
            }
            misc = MiscellaneousFeeSpecification.objects.create(
                code=f"MF-{year.year_start}",
                description="Miscellaneous fees for all undergraduate students",
                total_unit_to=40,
                **fee_years,
            )
            misc.fees.add(
                *self._fees(year, data.MISCELLANEOUS_FEES, Fee.Types.MISCELLANEOUS_FEE)
            )
            other = OtherFeeSpecification.objects.create(
                code=f"OF-{year.year_start}",
                description="Other fees for all undergraduate students",
                student_type=Student.Types.STUDENT,
                **fee_years,
            )
            other.fees.add(*self._fees(year, data.OTHER_FEES, Fee.Types.OTHER_FEE))
            self.fee_specs[year.id] = (misc, other)

        # Laboratory fees only have one rate per subject, so they're for this year
        for subject in self.subjects.values():
            if subject.is_lab_subject:
                LaboratoryFee.objects.create(
                    academic_year=self.current_year,
                    subject=subject,
                    rate=data.LABORATORY_FEE,
                )

        for discount in data.DISCOUNTS:
            self.discounts[discount["name"]] = Discount.objects.create(
                type=Discount.Types.NORMAL,
                apply_to=[Discount.ApplyToCategories.TUITION_FEE],
                # Graduate rates are the only ones left out, so the discount
                # covers all undergraduate tuition
                category_rate_exemption=[CurriculumSubject.CategoryRates.GRADUATE],
                **discount,
            )

    def _fees(self, year, fees, fee_type):
        age = self.current_year.year_start - year.year_start
        factor = (1 - data.YEARLY_TUITION_INCREASE) ** age

        return [
            Fee.objects.create(
                academic_year=year,
                code=code,
                name=name,
                type=fee_type,
                amount=money(amount * factor),
            )
            for code, name, amount in fees
        ]

    # Classes and schedules

    def _class(self, semester, course_code, curriculum_subject, section=1):
        key = (semester.id, course_code, curriculum_subject.id, section)
        if key in self.classes:
            return self.classes[key]

        subject = curriculum_subject.subject
        year_level = curriculum_subject.curriculum_period.year_level
        kind = "professional" if subject.is_professional_subject else "general"
        department = self.subject_departments[subject.course_code]

        klass = Class.objects.create(
            subject=subject,
            instructor=self.rng.choice(self.faculty[department]),
            course=self.courses[course_code],
            semester=semester,
            tuition_fee_rate=self.tuition_rates[
                (semester.academic_year_id, kind, year_level)
            ],
            class_code=str(next(self.class_codes)),
            class_size=40,
            year_level=year_level,
        )
        block = (semester.id, course_code, year_level, section)
        self._schedule(klass, block, subject.is_lab_subject)

        self.classes[key] = klass
        return klass

    def _schedule(self, klass, block, is_lab):
        rooms = self.lab_rooms if is_lab else self.lecture_rooms
        school_id = klass.course.school_id
        rooms = sorted(rooms, key=lambda room: room.school_id != school_id)

        options = list(itertools.product(data.DAY_PAIRS, data.TIME_SLOTS))
        self.rng.shuffle(options)

        # Students in the same block never get two classes at the same time,
        # and a room is only used once per time slot
        for days, slot in options:
            if any((block, day, slot) in self.block_usage for day in days):
                continue

            for room in rooms:
                taken = any(
                    (klass.semester_id, room.id, day, slot) in self.room_usage
                    for day in days
                )
                if taken:
                    continue

                for day in days:
                    self.block_usage.add((block, day, slot))
                    self.room_usage.add((klass.semester_id, room.id, day, slot))
                    ClassSchedule.objects.create(
                        klass=klass,
                        room=room,
                        ref_id=f"{klass.class_code}-{day}",
                        day=day,
                        time_in=time.fromisoformat(slot[0]),
                        time_out=time.fromisoformat(slot[1]),
                    )
                return

    # Students and their records

    def create_students(self):
        student_role = Role.objects.get(name=ReservedRole.STUDENT)

        for index in range(self.student_count):
            # The demo account is a second year who has paid in full and
            # hasn't started enrolling for next semester yet
            if index == 0:
                course_data, year_level = data.COURSES[0], 2
                payment_plan, next_semester = "paid", None
            else:
                course_data = data.COURSES[index % len(data.COURSES)]
                year_level = index // len(data.COURSES) % 4 + 1
                payment_plan = {3: "minimum", 4: "partial"}.get(index % 5, "paid")
                next_semester = None
                if payment_plan == "paid":
                    next_semester = {0: "enrolled", 1: "in_progress"}.get(index % 3)

            scholarship = None
            if index and index % 7 == 0:
                scholarship = self.discounts["Academic Scholarship"]
            elif index % 11 == 5:
                scholarship = self.discounts["Sibling Discount"]

            student = self._student(index, course_data, year_level, scholarship)
            student.user.groups.add(student_role)

            for semester, level, finished in self._timeline(year_level):
                enrollment = self._enroll(
                    student,
                    course_data["code"],
                    semester,
                    level,
                    discount=scholarship,
                    when=at(semester.date_start - timedelta(days=14)),
                )
                self._grade(enrollment, finished)
                plan = "paid" if finished else payment_plan
                self._pay_semester(enrollment, semester, plan)

            if next_semester:
                self.next_semester_plans.append(
                    (student, course_data["code"], scholarship, next_semester)
                )

    def _student(self, index, course_data, year_level, scholarship):
        gender = self.rng.choice(Student.Genders.values)
        first_name, last_name = self._name(gender)
        middle_name = self.rng.choice(
            [name for name in data.LAST_NAMES if name != last_name]
        )

        admission_year = self.years[-year_level].year_start
        id_number = f"{admission_year}-{index + 1:05d}"
        username = STUDENT_USERNAME if index == 0 else id_number
        email_name = f"{slugify(first_name)}.{slugify(last_name)}{index + 1}"

        user = User.objects.create(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=f"{email_name}@{EMAIL_DOMAIN}",
            password=self.password,
            is_first_login=False,
        )
        user.password_histories.create(value=self.password)

        father = f"{self.rng.choice(data.MALE_FIRST_NAMES)} {last_name}"
        mother = f"{self.rng.choice(data.FEMALE_FIRST_NAMES)} {last_name}"
        street = self.fake.street_address()
        barangay = self.rng.choice(data.BARANGAYS)
        city = self.fake.province_lgu()
        province = self.fake.luzon_province()
        birth_year = self.today.year - 17 - year_level

        return Student.objects.create(
            user=user,
            type=Student.Types.STUDENT,
            status=Student.Statuses.SCHOLAR
            if scholarship
            else Student.Statuses.REGULAR,
            id_number=id_number,
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            birth_date=self.fake.date_between_dates(
                datetime(birth_year, 1, 1).date(), datetime(birth_year, 12, 28).date()
            ),
            birth_place=self.fake.province_lgu(),
            gender=gender,
            civil_status=Student.CivilStatuses.SINGLE,
            citizenship=Student.Citizenships.Filipino,
            nationality=Student.Nationalities.Filipino,
            email=f"{email_name}@example.com",
            institutional_email=user.email,
            phone_no=self.fake.mobile_number(),
            home_phone_no=self.fake.landline_number(),
            street=street,
            barangay=barangay,
            city=city,
            province=province,
            zip_code=self.fake.postcode(),
            father_name=father,
            father_occupation=self.fake.job(),
            mother_name=mother,
            mother_occupation=self.fake.job(),
            emergency_contact_name=mother,
            emergency_contact_address=f"{street}, {barangay}, {city}",
            emergency_contact_phone_no=self.fake.mobile_number(),
            course=self.courses[course_data["code"]],
            curriculum=self.courses[course_data["code"]].course_curriculums.get(),
            semester=self.semesters[(self.current_year.id, FS)],
            year_level=year_level,
            date_created=self.years[-year_level].date_start,
        )

    def _timeline(self, year_level):
        """Every term the student has enrolled in, as (semester, year level, finished)"""
        terms = []

        for level in range(1, year_level):
            year = self.years[level - year_level - 1]
            terms.append((self.semesters[(year.id, FS)], level, True))
            terms.append((self.semesters[(year.id, SS)], level, True))

        terms.append((self.semesters[(self.current_year.id, FS)], year_level, False))
        return terms

    def _enroll(
        self,
        student,
        course_code,
        semester,
        year_level,
        *,
        discount,
        when,
        status=Enrollment.Statuses.ENROLLED,
        section=1,
    ):
        misc, other = self.fee_specs[semester.academic_year_id]
        enrolled = status == Enrollment.Statuses.ENROLLED

        enrollment = Enrollment.objects.create(
            student=student,
            academic_year=semester.academic_year,
            semester=semester,
            status=status,
            step=Enrollment.Steps.STATUS if enrolled else Enrollment.Steps.PAYMENT,
            year_level=year_level,
            current_address=student.address,
            contact_number=student.phone_no,
            home_contact_number=student.home_phone_no,
            personal_email=student.email,
            institutional_email=student.institutional_email,
            father_name=student.father_name,
            father_occupation=student.father_occupation,
            mother_name=student.mother_name,
            mother_occupation=student.mother_occupation,
            emergency_contact_name=student.emergency_contact_name,
            emergency_contact_address=student.emergency_contact_address,
            emergency_contact_phone_no=student.emergency_contact_phone_no,
            miscellaneous_fee_specification=misc,
            other_fee_specification=other,
        )
        EnrollmentDiscount.objects.create(
            enrollment=enrollment, validated_discount=discount
        )
        EnrollmentStatus.objects.create(
            enrollment=enrollment,
            block_status=EnrollmentStatus.BlockStatuses.PASSED,
        )
        enrollment.events.create(event=EnrollmentEvent.Events.ENROLLMENT_STARTED)

        period = self.periods[(course_code, year_level, semester.term)]
        class_status = (
            EnrolledClass.Statuses.ENROLLED
            if enrolled
            else EnrolledClass.Statuses.RESERVED
        )
        for curriculum_subject in period.curriculum_subjects.select_related(
            "subject", "curriculum_period"
        ):
            EnrolledClass.objects.create(
                student=student,
                enrollment=enrollment,
                klass=self._class(semester, course_code, curriculum_subject, section),
                curriculum_subject=curriculum_subject,
                status=class_status,
            )

        backdate(enrollment, when)
        soa_create(enrollment=enrollment)
        return enrollment

    def _grade(self, enrollment, finished):
        if not finished:
            return

        # Grades in the same term stay close to each other
        ability = self.rng.randint(80, 94)
        finals = []

        for enrolled_class in enrollment.enrolled_classes.all():
            final = min(max(ability + self.rng.randint(-6, 5), 75), 99)
            finals.append(final)

            EnrolledClassGrade.objects.create(
                enrolled_class=enrolled_class,
                prelim_grade=min(final + self.rng.randint(-4, 4), 99),
                midterm_grade=min(final + self.rng.randint(-4, 4), 99),
                tentative_final_grade=final,
                final_grade=final,
                prelim_grade_state=GradeStates.SUBMITTED,
                midterm_grade_state=GradeStates.SUBMITTED,
                tentative_final_grade_state=GradeStates.SUBMITTED,
                final_grade_state=GradeStates.SUBMITTED,
                status=EnrolledClassGrade.Statuses.PASSED,
            )

        EnrollmentGrade.objects.create(
            enrollment=enrollment,
            general_weighted_average=money(Decimal(sum(finals)) / len(finals)),
            pass_percentage=100,
            grading_status=EnrollmentGrade.GradingStatuses.PASSED,
        )

    def _pay_semester(self, enrollment, semester, plan):
        soa = enrollment.statement_of_account
        balance = soa.get_remaining_balance()
        first_payment = min(money(soa.min_amount), balance)

        # Students pay the minimum at enrollment and the rest before prelims
        payments = [
            (first_payment, semester.date_start - timedelta(days=10)),
            (balance - first_payment, semester.prelim_date_start - timedelta(days=5)),
        ]
        if plan == "minimum":
            payments = payments[:1]
        elif plan == "partial":
            payments[1] = (money((balance - first_payment) / 2), payments[1][1])

        for amount, day in payments:
            if amount > 0 and day <= self.today:
                self._pay(soa, amount, at(day, hour=self.rng.randint(8, 16)))

        if plan == "paid":
            enrollment.events.create(event=EnrollmentEvent.Events.ENROLLMENT_ENDED)

    def _pay(self, soa, amount, when):
        if self.rng.random() < 0.6:
            # Sent the day before and validated by finance the next day
            payment = self._fund_transfer(
                soa,
                amount,
                when - timedelta(days=1),
                status=OverTheCounterTransaction.Statuses.SETTLED,
                settled_at=when,
                validated_at=when,
                validated_by=self.admin,
            )
            description = f"Fund transfer {payment.bank} {payment.transfer_reference}"
        else:
            payment = CashierTransaction.objects.create(
                soa=soa,
                amount=amount,
                status=CashierTransaction.Statuses.SETTLED,
                receipt_id=f"OR-{next(self.receipt_numbers):06d}",
                processed_at=when,
                processed_by=self.admin,
                settled_at=when,
            )
            description = "Cashier payment"

        payment.generate_id()
        transaction = AccountTransaction.objects.create(
            soa=soa,
            student=soa.enrollment.student,
            amount=-amount,
            description=description,
            ref=payment,
        )
        backdate(payment, when)
        backdate(transaction, when)

    def _fund_transfer(self, soa, amount, submitted_at, **fields):
        bank = self.rng.choice(list(settings.UNIVERSITY_PAYMENT_BANK_ACCOUNTS))
        reference = f"FT{self.rng.randint(10**9, 10**10 - 1)}"

        payment = OverTheCounterTransaction.objects.create(
            soa=soa,
            bank=bank,
            amount=amount,
            transfer_reference=reference,
            transfer_date=timezone.localtime(submitted_at).date(),
            submitted_at=submitted_at,
            **fields,
        )
        payment.receipt.save(
            "receipt.pdf",
            ContentFile(receipt_pdf(bank, reference, amount, submitted_at)),
            save=False,
        )
        payment.generate_id()
        return payment

    # Next semester's enrollment

    def open_enrollment(self):
        semester = self.semesters[(self.current_year.id, SS)]

        # Two sections of everything offered next semester
        for course_code in self.courses:
            for year_level in range(1, 5):
                period = self.periods[(course_code, year_level, SS)]
                for curriculum_subject in period.curriculum_subjects.select_related(
                    "subject", "curriculum_period"
                ):
                    for section in (1, 2):
                        self._class(semester, course_code, curriculum_subject, section)

        config = ModuleConfiguration.objects.get(
            module__codename=MobileModule.ENROLLMENT
        )
        for year_level in range(1, 5):
            schedule = EnrollmentSchedule.objects.create(
                config=config,
                academic_year=self.current_year,
                semester=semester,
                year_level=year_level,
                start_datetime=self.now - timedelta(days=3),
                end_datetime=self.now + timedelta(days=30),
            )
            # The beat task would normally do this when the schedule starts
            enrollment_start(schedule=schedule)
            schedule.events.create(event=events.ENROLLMENT_STARTED)

        enrollment_role = Role.objects.get(name=ReservedRole.STUDENT_ENROLLMENT)

        # Half the students still choosing classes have sent a transfer that
        # finance hasn't validated yet. The first one is already overdue.
        waiting = itertools.cycle([True, False])
        overdue = True

        for student, course_code, discount, plan in self.next_semester_plans:
            enrolled = plan == "enrolled"
            enrollment = self._enroll(
                student,
                course_code,
                semester,
                student.year_level,
                discount=discount,
                when=self.now - timedelta(days=self.rng.randint(0, 2)),
                status=(
                    Enrollment.Statuses.ENROLLED
                    if enrolled
                    else Enrollment.Statuses.ENROLLMENT
                ),
                section=self.rng.choice([1, 2]),
            )

            soa = enrollment.statement_of_account

            if enrolled:
                self._pay(soa, money(soa.min_amount), self.now - timedelta(hours=6))
                student.user.groups.remove(enrollment_role)
            elif next(waiting):
                hours = 72 if overdue else self.rng.randint(2, 30)
                self._fund_transfer(
                    soa,
                    money(soa.min_amount),
                    self.now - timedelta(hours=hours),
                    status=OverTheCounterTransaction.Statuses.FOR_VALIDATION,
                )
                overdue = False

    def create_announcements(self):
        next_semester = self.semesters[(self.current_year.id, SS)]
        first_semester = self.semesters[(self.current_year.id, FS)]
        year = self.current_year

        Announcement.objects.create(
            start_date=self.now - timedelta(days=3),
            end_date=self.now + timedelta(days=30),
            subject=(
                f"Enrollment for the {next_semester.get_term_display()}, "
                f"AY {year.year_start}-{year.year_end}, is open"
            ),
            content=(
                "Students with no outstanding balance can now choose their classes "
                "for next semester. Reserved slots are held until the minimum "
                "payment is made."
            ),
        )
        Announcement.objects.create(
            start_date=self.now - timedelta(days=10),
            end_date=at(first_semester.final_date_end),
            subject="Final examination schedule",
            content=(
                f"Final examinations run from {first_semester.final_date_start:%B %d} "
                f"to {first_semester.final_date_end:%B %d}. Settle your balance "
                "before the exam week to get your exam permit."
            ),
        )
