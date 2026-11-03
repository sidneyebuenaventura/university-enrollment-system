from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from university.core.accounts.models import (
    AcademicYear,
    Department,
    Personnel,
    School,
    Semester,
)
from university.framework.models import (
    BaseModel,
    PolymorphicSoftDeleteModel,
    SoftDeleteModel,
    TextChoiceField,
)

User = get_user_model()


class Semesters(models.TextChoices):
    FIRST_SEMESTER = "FS", "First Semester"
    SECOND_SEMESTER = "SS", "Second Semester"
    SUMMER = "S", "Summer"


class Course(SoftDeleteModel):
    class Levels(models.TextChoices):
        ASSOCIATE = "A", "Associate/Certificate"
        BACHELOR_DEGREE = "B", "Bachelor Degree"
        MASTERAL = "M", "Masteral"
        DOCTORAL = "D", "Doctoral"
        POST_GRADUATE = "P", "Post Graduate"
        SPECIAL_PROGRAM = "1", "Special Program"

    class Categories(models.TextChoices):
        MEDICAL_LABORATORY_SCIENCE = "MLS", "Medical Laboratory Science"
        MASTERAL = "M", "Masteral"
        BUSINESS_ADMINISTRATION = "BA", "Business Administration"
        HOSPITALITY_AND_TOURISM_MANAGEMENT = "HM", "Hospitality and Tourism Management"
        PHILOSOPHY = "P", "Philosophy"
        EDUCATION = "E", "Education"
        ENGLISH = "EN", "English"
        LAW = "L", "Law"
        MEDICAL_TECHNOLOGY = "MT", "Medical Technology"
        ACCOUNTANCY = "ACC", "Accountancy"
        DOCTORAL = "D", "Doctoral"
        MATHEMATICS = "MATH", "Mathematics"
        ENGINEERING = "ENGG", "ENGINEERING"
        RADIOLOGIC_TECHNOLOGY = "RT", "Radiologic Technology"
        INFO_TECHNOLOGY = "IT", "Info Technology"
        COMMERCE = "C", "Commerce"
        ARCHITECTURE = "ARC", "Architecture"
        COMPUTER_SCIENCE = "CS", "Computer Science"
        AB = "AB", "AB"
        ECONOMICS = "ECO", "Economics"
        LITERATURE = "LIT", "Literature"
        MANAGEMENT_ACCOUNTING = "MACC", "Management Accounting"
        BIOLOGY = "BIO", "Biology"
        LEGAL_STUDIES = "LS", "Legal Studies"
        COMMUNICATION = "COMM", "Communication"
        POLITICAL_SCIENCE = "PS", "Political Science"
        INTERDISCIPLINARY_STUDIES = "IS", "Interdisciplinary Studies"
        STATISTICS = "STAT", "Statistics"
        PSYCHOLOGY = "PSY", "Psychology"
        SOCIAL_WORK = "SW", "Social Work"
        SOCIOLOGY = "SOC", "Sociology"
        PHARMACY = "PH", "Pharmacy"
        NURSING = "N", "Nursing"
        MEDICINE = "MED", "Medicine"

    class DurationUnits(models.TextChoices):
        YEAR = "Y", "Year"
        MONTH = "M", "Month"

    school = models.ForeignKey(
        School, on_delete=models.SET_NULL, blank=True, null=True, related_name="courses"
    )
    level = TextChoiceField(
        max_length=2,
        choices_cls=Levels,
        blank=True,
        null=True,
    )

    category = TextChoiceField(
        max_length=5,
        choices_cls=Categories,
        blank=True,
        null=True,
    )

    code = models.CharField(max_length=50)
    sub_code = models.CharField(max_length=50)
    name = models.CharField(max_length=250)
    major = models.CharField(max_length=250, blank=True, null=True)
    minor = models.CharField(max_length=250, blank=True, null=True)
    is_accredited = models.BooleanField(default=True)
    accredited_year = models.CharField(max_length=50, blank=True, null=True)
    has_board_exam = models.BooleanField(default=True)
    duration = models.CharField(max_length=20, blank=True, null=True)
    duration_unit = TextChoiceField(
        max_length=20,
        choices_cls=DurationUnits,
        default=DurationUnits.YEAR,
        blank=True,
        null=True,
    )
    degree_class = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.name


class Curriculum(SoftDeleteModel):
    course = models.ForeignKey(
        "Course", on_delete=models.CASCADE, related_name="course_curriculums"
    )

    ref_id = models.CharField(max_length=50)
    effective_start_year = models.IntegerField()
    effective_end_year = models.IntegerField()
    effective_semester = TextChoiceField(
        max_length=50, choices_cls=Semesters, default=Semesters.FIRST_SEMESTER
    )

    is_current = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.effective_start_year}-{self.effective_end_year} {self.effective_semester} {self.course.name}"


class CurriculumPeriod(SoftDeleteModel):
    curriculum = models.ForeignKey(
        "Curriculum", on_delete=models.CASCADE, related_name="curriculum_periods"
    )
    semester = TextChoiceField(
        max_length=50, choices_cls=Semesters, blank=True, null=True
    )
    year_level = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(5)], blank=True, null=True
    )
    order = models.IntegerField(null=True)

    def __str__(self):
        return f"{self.curriculum} - {self.semester}-{self.year_level}"

    def get_total_units(self) -> Decimal:
        return sum(
            [
                curriculum_subj.subject.units
                for curriculum_subj in self.curriculum_subjects.all()
            ]
        )

    def get_total_category_units(self, category) -> Decimal:
        return sum(
            [
                curriculum_subj.subject.units
                for curriculum_subj in self.subjects.filter(subject_class=category)
            ]
        )


class CurriculumSubject(SoftDeleteModel):
    class SubjectClasses(models.TextChoices):
        MAJOR = "M", "Major"
        ELECTIVE = "E", "Elective"
        SPECIALIZATION = "S", "Specialization"

    class CategoryRates(models.TextChoices):
        PROFESSIONAL_EDUCATION = "PE", "Professional Education"
        NON_PROFESSIONAL = "NP", "Non-Professional"
        IT_RATE = "ITR", "IT Rate"
        NURSE_RATE = "NR", "Nurse Rate"
        LLB_RATE = "LR", "LLB Rate"
        GRADUATE = "G", "Graduate"

    curriculum = models.ForeignKey(
        "Curriculum",
        on_delete=models.SET_NULL,
        related_name="subjects",
        blank=True,
        null=True,
    )
    curriculum_period = models.ForeignKey(
        "CurriculumPeriod",
        on_delete=models.SET_NULL,
        related_name="curriculum_subjects",
        blank=True,
        null=True,
    )
    subject = models.ForeignKey(
        "Subject", on_delete=models.CASCADE, related_name="subject_curriculum_periods"
    )

    subject_class = TextChoiceField(
        max_length=20, choices_cls=SubjectClasses, blank=True, null=True
    )
    category_rate = TextChoiceField(
        max_length=20, choices_cls=CategoryRates, blank=True, null=True
    )
    lec_hrs = models.IntegerField(default=0)
    lab_wk = models.IntegerField(default=0)
    order = models.IntegerField()

    def __str__(self):
        return f"{self.curriculum_period.curriculum.id} - {self.curriculum_period.semester}-{self.curriculum_period.year_level} - {self.subject.ref_id}"

    def has_pending_prerequisite(self, passed_curr_subj_ids: list[int]):
        return (
            self.requisites.filter(type=CurriculumSubjectRequisite.Types.PRE_REQUISITE)
            .filter(~Q(id__in=passed_curr_subj_ids))
            .count()
            > 0
        )


class CurriculumSubjectRequisite(SoftDeleteModel):
    class Types(models.TextChoices):
        PRE_REQUISITE = "P", "Pre-Requisite"
        CO_REQUISITE = "C", "Co-Requisite"

    curriculum_subject = models.ForeignKey(
        CurriculumSubject,
        on_delete=models.CASCADE,
        related_name="requisites",
    )
    requisite_subject = models.ForeignKey(
        CurriculumSubject,
        on_delete=models.CASCADE,
        related_name="requisite_tags",
    )
    type = TextChoiceField(
        max_length=20, choices_cls=Types, default=Types.PRE_REQUISITE
    )

    def __str__(self):
        return f"{self.type} - {self.curriculum_subject.subject.descriptive_code} : {self.requisite_subject.subject.descriptive_code}"


class Class(SoftDeleteModel):
    """use klass variable name in pertaining to this model"""

    subject = models.ForeignKey(
        "Subject", on_delete=models.SET_NULL, related_name="classes", null=True
    )
    instructor = models.ForeignKey(
        Personnel,
        on_delete=models.SET_NULL,
        related_name="subject_classes",
        blank=True,
        null=True,
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        related_name="classes",
        blank=True,
        null=True,
    )
    semester = models.ForeignKey(
        Semester,
        on_delete=models.SET_NULL,
        related_name="classes",
        null=True,
    )
    tuition_fee_rate = models.ForeignKey(
        "TuitionFeeRate",
        on_delete=models.SET_NULL,
        related_name="classes",
        blank=True,
        null=True,
    )

    class_code = models.CharField(max_length=50, db_index=True)
    class_size = models.IntegerField(default=0)

    is_dissolved = models.BooleanField(default=False)
    is_crash_course = models.BooleanField(default=False)
    is_intercollegiate = models.BooleanField(default=False)
    is_external_class = models.BooleanField(default=False)

    year_level = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(5)], default=1
    )

    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        if self.subject:
            return f"{self.class_code} - {self.subject.descriptive_code} - {self.subject.descriptive_title}"
        return self.class_code

    def get_total_students_enrolled(self) -> Decimal:
        from university.core.students.models import EnrolledClass

        statuses = [EnrolledClass.Statuses.RESERVED, EnrolledClass.Statuses.ENROLLED]
        return self.enrollments.filter(status__in=statuses).count()

    def has_available_slot_for_reservation(self) -> bool:
        return self.get_total_students_enrolled() < self.class_size


class ClassGradeState(BaseModel):
    class States(models.TextChoices):
        EMPTY = "E", "Empty"
        DRAFT = "D", "Draft"
        SUBMITTED = "S", "Submitted"

    klass = models.OneToOneField(
        "Class",
        on_delete=models.CASCADE,
        related_name="grade_states",
    )

    prelim_grade_state = TextChoiceField(
        max_length=1, choices_cls=States, default=States.EMPTY
    )
    midterm_grade_state = TextChoiceField(
        max_length=1, choices_cls=States, default=States.EMPTY
    )
    tentative_final_grade_state = TextChoiceField(
        max_length=1, choices_cls=States, default=States.EMPTY
    )
    final_grade_state = TextChoiceField(
        max_length=1, choices_cls=States, default=States.EMPTY
    )


class ClassSchedule(BaseModel):
    class Days(models.TextChoices):
        MONDAY = "M", "Monday"
        TUESDAY = "T", "Tuesday"
        WEDNESDAY = "W", "Wednesday"
        THURSDAY = "TH", "Thursday"
        FRIDAY = "F", "Friday"
        SATURDAY = "S", "Saturday"

    klass = models.ForeignKey(
        "Class",
        on_delete=models.CASCADE,
        related_name="class_schedules",
    )
    room = models.ForeignKey(
        "Room",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="class_schedules",
    )

    ref_id = models.CharField(max_length=50)
    time_in = models.TimeField(null=True)
    time_out = models.TimeField(null=True)
    day = TextChoiceField(max_length=20, choices_cls=Days, default=Days.MONDAY)

    def __str__(self):
        return self.ref_id

    def is_valid(self):
        return self.room and self.time_in and self.time_out


class Classification(BaseModel):
    ref_id = models.CharField(max_length=50)
    name = models.CharField(max_length=255, db_index=True)

    def __str__(self):
        return self.name


class Building(BaseModel):
    ref_id = models.CharField(max_length=50, db_index=True)
    sub_code = models.CharField(max_length=50, blank=True, null=True)
    no_of_floors = models.IntegerField(blank=True, null=True)
    name = models.CharField(max_length=255)
    schools = models.ManyToManyField(
        School, blank=True, related_name="school_buildings"
    )
    campus = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Room(SoftDeleteModel):
    school = models.ForeignKey(
        School,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="school_rooms",
    )
    classification = models.ForeignKey(
        "Classification",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="classification_rooms",
    )
    building = models.ForeignKey(
        "Building",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="building_rooms",
    )
    number = models.CharField(max_length=150, db_index=True)
    name = models.CharField(max_length=250, blank=True, null=True)
    size = models.CharField(max_length=150, blank=True, null=True)
    floor_no = models.IntegerField(blank=True, null=True)
    wing = models.CharField(max_length=100, blank=True, null=True)
    capacity = models.IntegerField(blank=True, null=True)
    furniture = models.CharField(max_length=250, blank=True, null=True)
    is_lecture_room = models.BooleanField(default=True)

    def __str__(self):
        return self.number


class SubjectGrouping(SoftDeleteModel):
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="subject_groupings",
    )
    ref_id = models.CharField(max_length=50, db_index=True)
    name = models.CharField(max_length=250, blank=True, null=True)
    group_course = models.TextField(blank=True, null=True)
    is_gen_ed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.ref_id} - {self.name}"


class Subject(SoftDeleteModel):
    class Categories(models.TextChoices):
        LECTURE = "LEC", "Lecture"
        LABORATORY = "LAB", "Laboratory"

    class Types(models.TextChoices):
        NONE = "N", "None"
        PRE_REQUISITE = "P", "Pre-Requisite"
        CO_REQUISITE = "C", "Co-Requisite"

    class LabCategories(models.TextChoices):
        ACCOUNTING = "A", "Accounting"
        COMPUTER = "C", "Computer"
        GRADUATE_PROGRAM = "G", "Graduate Program"
        LABORATORY = "L", "Laboratory"
        LAW = "W", "Law"
        MEDICINE = "M", "Medicine"
        PE = "P", "PE"
        RELIGION = "R", "Religion"

    class Classifications(models.TextChoices):
        BSIM_BLIS = "F", "BSIM/BLIS"
        DAP = "D", "DAP"
        GRADUATE = "G", "Graduate"
        LAW = "L", "LAW"
        MEDICINE = "M", "MEDICINE"
        PE = "P", "PE (Minor)"
        R = "R", "RSTC"
        N = "N", "NSTP"
        NONE = "NONE", "Normal Subject"

    class SubTypes(models.TextChoices):
        AS_CMT_ROTC_11 = "A11", "AS/CMT/ROTC 11"
        AS_CMT_ROTC_12 = "A12", "AS/CMT/ROTC 12"
        AS_CMT_ROTC_21 = "A21", "AS/CMT/ROTC 21"
        AS_CMT_ROTC_22 = "A22", "AS/CMT/ROTC 22"
        AS_CMT_ROTC_31 = "A31", "AS/CMT/ROTC 31"
        AS_CMT_ROTC_32 = "A32", "AS/CMT/ROTC 32"
        AS_CMT_ROTC_41 = "A41", "AS/CMT/ROTC 41"
        AS_CMT_ROTC_42 = "A42", "AS/CMT/ROTC 42"
        PE_1 = "PE1", "PE 1"
        PE_2 = "PE2", "PE 2"
        PE_3 = "PE3", "PE 3"
        PE_4 = "PE4", "PE 4"

    class Durations(models.TextChoices):
        YEARLY = "Y", "Yearly"
        SEMESTRAL = "S", "Semestral"
        MONTHLY = "M", "Monthly"

    school = models.ForeignKey(
        School, on_delete=models.SET_NULL, blank=True, null=True, related_name="rooms"
    )
    grouping = models.ForeignKey(
        SubjectGrouping,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="grouping_subjects",
    )

    ref_id = models.CharField(max_length=100)
    charge_code = models.CharField(max_length=50, blank=True, null=True)
    course_code = models.CharField(max_length=100, blank=True, null=True)
    course_number = models.CharField(max_length=100, blank=True, null=True)
    descriptive_code = models.CharField(max_length=100, blank=True, null=True)
    descriptive_title = models.CharField(max_length=250, blank=True, null=True)

    is_professional_subject = models.BooleanField(default=False)
    is_lab_subject = models.BooleanField(default=False)
    lab_category = TextChoiceField(
        max_length=20, choices_cls=LabCategories, blank=True, null=True
    )

    sub_type = TextChoiceField(
        max_length=20,
        choices_cls=SubTypes,
        blank=True,
        null=True,
    )
    classification = TextChoiceField(
        max_length=20,
        choices_cls=Classifications,
        blank=True,
        null=True,
    )
    category = TextChoiceField(
        max_length=20,
        choices_cls=Categories,
        blank=True,
        null=True,
    )

    units = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Only for Non-Medicine Subjects",
    )
    no_of_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Only for Medicine Subjects",
    )
    duration = TextChoiceField(
        max_length=20, choices_cls=Durations, blank=True, null=True
    )

    def __str__(self):
        return f"{self.course_code} - {self.descriptive_title}"


class Fee(SoftDeleteModel):
    class Types(models.TextChoices):
        MISCELLANEOUS_FEE = "M", "Miscellaneous Fee"
        OTHER_FEE = "O", "Other Fee"

    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.SET_NULL,
        related_name="fees",
        null=True,
    )

    code = models.CharField(max_length=50)
    name = models.CharField(max_length=250, blank=True, null=True)
    description = models.CharField(max_length=250, blank=True, null=True)
    type = TextChoiceField(max_length=10, choices_cls=Types)
    remarks = models.TextField(blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.code} - {self.name}"


class Discount(SoftDeleteModel):
    class Types(models.TextChoices):
        SCHOLARSHIP = "S", "Scholarship"
        NORMAL = "N", "Normal"

    class ApplyToCategories(models.TextChoices):
        TUITION_FEE = "TF", "Tuition Fee"
        LABORATORY_FEE = "LF", "Laboratory Fee"
        OTHER_FEE = "OF", "Other Fee"
        MISCELLANEOUS_FEE = "MF", "Miscellaneous Fee"

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="discounts",
    )

    type = TextChoiceField(max_length=10, choices_cls=Types, blank=True, null=True)
    apply_to = models.JSONField(default=list)
    ref_id = models.CharField(max_length=50)
    name = models.CharField(max_length=250)
    percentage = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    remarks = models.TextField(blank=True, null=True)
    is_confirmed = models.BooleanField(default=True)

    fee_exemptions = models.ManyToManyField(
        Fee, blank=True, related_name="exempted_discounts"
    )
    category_rate_exemption = models.JSONField(default=list)

    def __str__(self):
        return f"{self.name} - {self.percentage}%"


class RemarkCode(SoftDeleteModel):
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="communication_codes",
    )
    ref_id = models.CharField(max_length=50)
    description = models.TextField()

    def __str__(self):
        return f"{self.ref_id} - {self.description}"


class FeeSpecification(PolymorphicSoftDeleteModel):
    school = models.ForeignKey(
        School,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="school_fee_specifications",
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="subject_fee_specifications",
    )

    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.SET_NULL,
        related_name="fee_specifications",
        null=True,
    )

    code = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)

    semester_from = TextChoiceField(
        max_length=10, choices_cls=Semesters, blank=True, null=True
    )
    semester_to = TextChoiceField(
        max_length=10, choices_cls=Semesters, blank=True, null=True
    )

    year_level_from = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    year_level_to = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )

    fees = models.ManyToManyField(Fee, blank=True)

    def get_handler(self):
        raise NotImplementedError


class MiscellaneousFeeSpecification(FeeSpecification):
    total_unit_from = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_unit_to = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"MF | {self.code} - {self.academic_year}"


class OtherFeeSpecification(FeeSpecification):
    from university.core.students.models import Student

    subject_group = models.ForeignKey(
        SubjectGrouping,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="subject_group_specifications",
    )

    student_type = TextChoiceField(
        max_length=5, choices_cls=Student.Types, blank=True, null=True
    )
    course_category = TextChoiceField(
        max_length=10, choices_cls=Course.Categories, blank=True, null=True
    )

    def __str__(self):
        return f"OF | {self.code} - {self.academic_year}"


class TuitionFeeCategory(SoftDeleteModel):
    class Categories(models.TextChoices):
        MSIT_MIT = "MSIT/MIT", "MSIT/MIT"
        DOCTORATE = "D", "Doctorate"
        PROFESSIONAL = "PRO", "Professional"
        NURSING = "N", "Nursing"
        GRAD_PROG_MASTERAL = "GPM", "Graduate Program (Masteral)"
        LLM_MASTERAL_LAW = "LLM", "LLM (Masteral Law)"
        COMPUTER_SCIENCE = "CS", "Computer Science"
        LAW = "L", "Law"
        NSTP = "NSTP", "NSTP"
        MSIT = "MSIT", "MSIT"
        GRADUATE_PROGRAM = "GP", "Graduate Program"
        NONPRO = "NP", "Non-Professional"

    ref_id = models.CharField(max_length=50)
    year_level = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    category = TextChoiceField(
        max_length=20, choices_cls=Categories, blank=True, null=True
    )

    def __str__(self):
        return f"{self.ref_id} | {self.year_level} -- {self.category}"


class TuitionFeeRate(SoftDeleteModel):
    tuition_fee_category = models.ForeignKey(
        TuitionFeeCategory,
        on_delete=models.CASCADE,
        related_name="rates",
    )
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.SET_NULL,
        related_name="tuition_fee_rates",
        null=True,
    )
    rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.academic_year}"


class LaboratoryFee(SoftDeleteModel):
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.SET_NULL,
        related_name="laboratory_fees",
        null=True,
    )
    rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subject = models.OneToOneField(
        Subject, related_name="laboratory_fee", on_delete=models.CASCADE, null=True
    )

    def __str__(self):
        return f"{self.name} - {self.academic_year}"


class Announcement(SoftDeleteModel):
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    subject = models.CharField(max_length=500)
    content = models.TextField()

    def __str__(self):
        return self.subject
