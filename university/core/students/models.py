import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from hashids import Hashids

from university.core.accounts.models import AcademicYear, Personnel, Semester
from university.core.cms.models import (
    Class,
    Course,
    Curriculum,
    CurriculumSubject,
    Discount,
    FeeSpecification,
    RemarkCode,
    Subject,
)
from university.framework.models import (
    BaseModel,
    PolymorphicBaseModel,
    SoftDeleteModel,
    TextChoiceField,
)
from university.framework.validators import csv_file_validator, excel_file_validator

User = get_user_model()


class Student(SoftDeleteModel):
    class Types(models.TextChoices):
        STUDENT = "S", "Student"
        FRESHMEN_APPLICANT = "FA", "Freshmen Applicant"

    class Statuses(models.TextChoices):
        REGULAR = "R", "Regular"
        SCHOLAR = "S", "Scholar"
        INTERNATIONAL = "I", "International"

    class Genders(models.TextChoices):
        MALE = "M", "Male"
        FEMALE = "F", "Female"

    class CivilStatuses(models.TextChoices):
        SINGLE = "S", "Single"
        MARRIED = "M", "Married"
        WIDOWED = "W", "Widowed"

    class Citizenships(models.TextChoices):
        Filipino = "F", "Filipino"

    class Nationalities(models.TextChoices):
        Filipino = "F", "Filipino"

    user = models.OneToOneField(User, on_delete=models.SET_NULL, blank=True, null=True)
    type = TextChoiceField(max_length=2, choices_cls=Types, default=Types.STUDENT)
    status = TextChoiceField(
        max_length=2, choices_cls=Statuses, default=Statuses.REGULAR
    )

    id_number = models.CharField(max_length=255, db_index=True)
    applicant_number = models.CharField(
        max_length=255, db_index=True, blank=True, null=True
    )
    is_previous_number = models.BooleanField(blank=True, null=True)

    first_name = models.CharField(max_length=255, db_index=True)
    middle_name = models.CharField(max_length=255, db_index=True, blank=True, null=True)
    last_name = models.CharField(max_length=255, db_index=True)

    birth_date = models.DateField(blank=True, null=True)
    birth_place = models.CharField(max_length=255, blank=True, null=True)
    gender = TextChoiceField(max_length=1, choices_cls=Genders, blank=True, null=True)

    civil_status = TextChoiceField(
        max_length=50, choices_cls=CivilStatuses, blank=True, null=True
    )
    citizenship = TextChoiceField(
        max_length=50, choices_cls=Citizenships, blank=True, null=True
    )
    nationality = TextChoiceField(
        max_length=50, choices_cls=Nationalities, blank=True, null=True
    )

    email = models.EmailField(blank=True, null=True)
    institutional_email = models.EmailField(null=True)
    phone_no = models.CharField(max_length=50, blank=True, null=True)

    street = models.CharField(max_length=250, blank=True, null=True)
    barangay = models.CharField(max_length=250, blank=True, null=True)
    city = models.CharField(max_length=250, blank=True, null=True)
    province = models.CharField(max_length=250, blank=True, null=True)
    zip_code = models.CharField(max_length=250, blank=True, null=True)
    home_phone_no = models.CharField(max_length=50, blank=True, null=True)

    local_address = models.CharField(max_length=250, blank=True, null=True)
    local_phone_no = models.CharField(max_length=250, blank=True, null=True)

    guardian_name = models.CharField(max_length=250, blank=True, null=True)
    guardian_address = models.CharField(max_length=250, blank=True, null=True)

    father_name = models.CharField(max_length=250, blank=True, null=True)
    father_occupation = models.CharField(max_length=250, blank=True, null=True)
    mother_name = models.CharField(max_length=250, blank=True, null=True)
    mother_occupation = models.CharField(max_length=250, blank=True, null=True)
    spouse_name = models.CharField(max_length=250, blank=True, null=True)
    spouse_address = models.CharField(max_length=250, blank=True, null=True)
    spouse_phone_no = models.CharField(max_length=250, blank=True, null=True)

    emergency_contact_name = models.CharField(max_length=250, blank=True, null=True)
    emergency_contact_address = models.CharField(max_length=255, null=True)
    emergency_contact_email = models.EmailField(blank=True, null=True)
    emergency_contact_phone_no = models.CharField(max_length=250, blank=True, null=True)

    religion = models.CharField(max_length=250, blank=True, null=True)
    senior_high_strand = models.CharField(max_length=250, blank=True, null=True)

    date_created = models.DateField(blank=True, null=True)

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="current_students",
        blank=True,
        null=True,
    )
    curriculum = models.ForeignKey(
        Curriculum,
        on_delete=models.CASCADE,
        related_name="current_students",
        blank=True,
        null=True,
    )
    semester = models.ForeignKey(
        Semester,
        on_delete=models.SET_NULL,
        related_name="students",
        blank=True,
        null=True,
    )
    year_level = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(25)], blank=True, null=True
    )

    def __str__(self):
        s = f"{self.id_number} - {self.last_name}, {self.first_name}"
        if self.middle_name:
            s = f"{s} {self.middle_name}"
        return s

    @property
    def address(self):
        return f"{self.street} {self.barangay} {self.city} {self.province}"


class Enrollment(BaseModel):
    class Statuses(models.TextChoices):
        PRE_ENROLLMENT = "PE", "Pre-Enrollment"
        PRE_ENROLLED = "PED", "Pre-Enrolled"
        ENROLLMENT = "E", "Enrollment"
        ENROLLED = "ED", "Enrolled"
        INVALID = "I", "Invalid"

    class Steps(models.TextChoices):
        START = "0", "Start"
        INFORMATION = "1", "Information"
        DISCOUNTS = "2", "Discounts"
        SUBJECTS = "3", "Subjects"
        PAYMENT = "4", "Payment"
        STATUS = "5", "Enrollment Status"

    ONGOING_STATUSES = [Statuses.PRE_ENROLLMENT, Statuses.ENROLLMENT]
    PRE_ENROLLMENT_STEPS = [
        Steps.START,
        Steps.INFORMATION,
        Steps.DISCOUNTS,
        Steps.SUBJECTS,
    ]
    ENROLLMENT_STEPS = [
        # Temporarily: Allow Saving of Step 1 (Information) during enrollment
        # as we skipped Pre-Enrollment process.
        Steps.INFORMATION,
        Steps.DISCOUNTS,
        Steps.SUBJECTS,
        Steps.PAYMENT,
        Steps.STATUS,
    ]

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="enrollments"
    )

    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.SET_NULL,
        related_name="enrollments",
        null=True,
    )
    semester = models.ForeignKey(
        Semester,
        on_delete=models.SET_NULL,
        related_name="enrollments",
        null=True,
    )

    status = TextChoiceField(
        max_length=3, choices_cls=Statuses, default=Statuses.PRE_ENROLLMENT
    )

    year_level = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(25)], blank=True, null=True
    )

    current_address = models.CharField(max_length=255, null=True)
    contact_number = models.CharField(max_length=255, null=True)
    home_contact_number = models.CharField(max_length=255, null=True)
    personal_email = models.EmailField(null=True)
    institutional_email = models.EmailField(null=True)

    father_name = models.CharField(max_length=255, blank=True, null=True)
    father_occupation = models.CharField(max_length=255, blank=True, null=True)
    father_phone_no = models.CharField(max_length=255, blank=True, null=True)
    father_email = models.EmailField(blank=True, null=True)

    mother_name = models.CharField(max_length=255, blank=True, null=True)
    mother_occupation = models.CharField(max_length=255, blank=True, null=True)
    mother_phone_no = models.CharField(max_length=255, blank=True, null=True)
    mother_email = models.EmailField(blank=True, null=True)

    is_living_with_parents = models.BooleanField(default=True)

    emergency_contact_name = models.CharField(max_length=255, null=True)
    emergency_contact_address = models.CharField(max_length=255, null=True)
    emergency_contact_phone_no = models.CharField(max_length=255, null=True)
    emergency_contact_email = models.EmailField(blank=True, null=True)

    step = TextChoiceField(max_length=2, choices_cls=Steps, default=Steps.START)

    # NOTE: Remove upon business rules re Fee Specification finalization
    miscellaneous_fee_specification = models.ForeignKey(
        FeeSpecification,
        on_delete=models.SET_NULL,
        related_name="misc_enrollments",
        blank=True,
        null=True,
    )
    other_fee_specification = models.ForeignKey(
        FeeSpecification,
        on_delete=models.SET_NULL,
        related_name="other_enrollments",
        blank=True,
        null=True,
    )

    def __str__(self):
        return f"{self.student} - {self.semester.term} | {self.year_level}"


class EnrollmentDiscount(BaseModel):
    class DependentRelationships(models.TextChoices):
        FATHER = "F", "Father"
        MOTHER = "M", "Mother"

    enrollment = models.OneToOneField(
        Enrollment, on_delete=models.CASCADE, related_name="discounts"
    )
    is_employee = models.BooleanField(default=False)
    personnel = models.ForeignKey(
        Personnel,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="is_employee_discounts",
    )

    is_employee_dependent = models.BooleanField(default=False)
    dependent_personnel = models.ForeignKey(
        Personnel,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="is_employee_dependent_discounts",
    )
    dependent_relationship = TextChoiceField(
        max_length=2, choices_cls=DependentRelationships, blank=True, null=True
    )

    is_working_scholar = models.BooleanField(default=False)

    has_enrolled_sibling = models.BooleanField(default=False)
    siblings = models.ManyToManyField(
        Student, blank=True, related_name="sibling_discounts"
    )

    validated_discount = models.ForeignKey(
        Discount,
        on_delete=models.SET_NULL,
        related_name="discount_enrollments",
        blank=True,
        null=True,
        help_text="Validated discount that should be reflected on SOA",
    )


class EnrollmentGrade(BaseModel):
    class GradingStatuses(models.TextChoices):
        PENDING = "PN", "Pending"
        PASSED = "P", "Passed"
        FAILED = "F", "Failed"

    enrollment = models.OneToOneField(
        Enrollment, on_delete=models.CASCADE, related_name="grade"
    )
    general_weighted_average = models.DecimalField(
        max_digits=10, decimal_places=5, blank=True, null=True
    )
    pass_percentage = models.DecimalField(
        max_digits=10, decimal_places=5, blank=True, null=True
    )
    grading_status = TextChoiceField(
        max_length=2, choices_cls=GradingStatuses, default=GradingStatuses.PENDING
    )
    remark_code = models.ForeignKey(
        RemarkCode,
        on_delete=models.SET_NULL,
        related_name="enrollments",
        blank=True,
        null=True,
    )


class EnrollmentEvent(BaseModel):
    class Events(models.TextChoices):
        ENROLLMENT_STARTED = "ES", "Enrollment Started"
        ENROLLMENT_ENDED = "EE", "Enrollment Ended"

    enrollment = models.ForeignKey(
        Enrollment, on_delete=models.CASCADE, related_name="events"
    )
    event = TextChoiceField(max_length=12, choices_cls=Events)

    def __str__(self):
        return self.event


class EnrollmentStatus(BaseModel):
    class BlockStatuses(models.TextChoices):
        PASSED = "P", "Passed"
        BLOCKED_WITH_OUTSTANDING_BALANCE = "BWOB", "Blocked with Outstanding Balance"
        BLOCKED_WITH_FAILED_SUBJECT = "BWFS", "Blocked with Failed Subject"
        BLOCKED_WITH_OUTSTANDING_AND_FAILED_GRADE = (
            "BWOBFG",
            "Blocked with Outstanding Balance and Failed Grade",
        )

    class RemarkCodes(models.TextChoices):
        FOR_CURRICULUM_CHANGE = "FCC", "For Curriculum Change"
        ALLOWED_TO_ENROLL = "ATE", "Allowed to Enroll"

    enrollment = models.OneToOneField(Enrollment, on_delete=models.CASCADE)
    block_status = TextChoiceField(
        max_length=10, choices_cls=BlockStatuses, blank=True, null=True
    )

    is_for_manual_tagging = models.BooleanField(default=False)
    is_temporary_allowed = models.BooleanField(default=False)

    evaluation_remarks = models.TextField(blank=True, null=True)
    remark_code = TextChoiceField(
        max_length=10, choices_cls=RemarkCodes, blank=True, null=True
    )

    def __str__(self):
        return f"{self.enrollment}"


class EnrolledClass(BaseModel):
    class Statuses(models.TextChoices):
        RESERVED = "R", "Reserved"
        ENROLLED = "E", "Enrolled"
        VOID = "V", "Void"

    student = models.ForeignKey(
        Student, on_delete=models.SET_NULL, null=True, related_name="enrolled_classes"
    )

    enrollment = models.ForeignKey(
        Enrollment, on_delete=models.CASCADE, related_name="enrolled_classes"
    )
    klass = models.ForeignKey(
        Class, on_delete=models.SET_NULL, null=True, related_name="enrollments"
    )

    curriculum_subject = models.ForeignKey(
        CurriculumSubject,
        on_delete=models.SET_NULL,
        null=True,
        related_name="enrolled_classes",
    )
    equivalent_subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="enrolled_classes",
    )

    status = TextChoiceField(
        max_length=2, choices_cls=Statuses, default=Statuses.RESERVED
    )
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Enrolled classes"


class GradeStatuses(models.TextChoices):
    PENDING = "PN", "Pending"
    PASSED = "P", "Passed"
    HIGH_PASSED = "HP", "High Passed"
    INCOMPLETE = "INC", "Incomplete"
    NO_FINAL_EXAMINATION = "NFE", "No Final Examination"
    DROP = "D", "Dropped"
    YEARLY = "Y", "Yearly"
    WITHDRAWAL_WITH_PERMISSION = "WP", "Withdrawal with Permission"
    FAILED = "F", "Failed"


class GradeStates(models.TextChoices):
    EMPTY = "E", "Empty"
    DRAFT = "D", "Draft"
    SUBMITTED = "S", "Submitted"


class GradeFields(models.TextChoices):
    PRELIM = "prelim_grade", "Prelim"
    MIDTERM = "midterm_grade", "Midterm"
    TENTATIVE_FINAL = "tentative_final_grade", "Tentative Final"
    FINAL = "final_grade", "Final"


class EnrolledClassGrade(BaseModel):
    Statuses = GradeStatuses  # Backwards compat

    EDITABLE_GRADE_STATES = [GradeStates.EMPTY, GradeStates.DRAFT]

    enrolled_class = models.OneToOneField(
        EnrolledClass, on_delete=models.CASCADE, related_name="grades"
    )

    prelim_grade = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    midterm_grade = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    tentative_final_grade = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    final_grade = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )

    prelim_grade_state = TextChoiceField(
        max_length=1, choices_cls=GradeStates, default=GradeStates.EMPTY
    )
    midterm_grade_state = TextChoiceField(
        max_length=1, choices_cls=GradeStates, default=GradeStates.EMPTY
    )
    tentative_final_grade_state = TextChoiceField(
        max_length=1, choices_cls=GradeStates, default=GradeStates.EMPTY
    )
    final_grade_state = TextChoiceField(
        max_length=1, choices_cls=GradeStates, default=GradeStates.EMPTY
    )

    status = TextChoiceField(
        max_length=5, choices_cls=Statuses, default=Statuses.PENDING
    )
    remarks = models.TextField(blank=True, null=True)


def grade_sheet_file_path(instance, filename):
    file_ext = filename.split(".")[-1]
    file_name = str(uuid.uuid4()).replace("-", "")
    return f"grade_sheets/{file_name}.{file_ext}"


class GradeSheet(BaseModel):
    class Statuses(models.TextChoices):
        PENDING = "P", "Pending"
        PROCESSING = "O", "Processing"
        FAILED = "F", "Failed"
        COMPLETED = "C", "Completed"

    HASHIDS = Hashids(
        settings.HASHIDS_GRADE_SHEET_SALT,
        min_length=settings.HASHIDS_MIN_LENGTH,
        alphabet=settings.HASHIDS_ALPHABET_ALPHA_ONLY,
    )

    klass = models.ForeignKey(
        Class, on_delete=models.CASCADE, related_name="grade_sheets"
    )

    file_id = models.CharField(max_length=255, null=True)
    file = models.FileField(
        upload_to=grade_sheet_file_path, validators=[excel_file_validator]
    )
    status = TextChoiceField(
        max_length=2, choices_cls=Statuses, default=Statuses.PENDING
    )
    error_message = models.TextField(blank=True)

    def __str__(self):
        return f"Grade Sheet {self.file_id}"

    def generate_id(self):
        self.file_id = self.HASHIDS.encode(self.id)
        self.save()


class GradeSheetRow(BaseModel):
    grade_sheet = models.ForeignKey(
        GradeSheet, on_delete=models.CASCADE, related_name="rows"
    )

    student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True)

    prelim_grade = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    midterm_grade = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    tentative_final_grade = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    final_grade = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )

    prelim_grade_state = TextChoiceField(
        max_length=1, choices_cls=GradeStates, default=GradeStates.EMPTY
    )
    midterm_grade_state = TextChoiceField(
        max_length=1, choices_cls=GradeStates, default=GradeStates.EMPTY
    )
    tentative_final_grade_state = TextChoiceField(
        max_length=1, choices_cls=GradeStates, default=GradeStates.EMPTY
    )
    final_grade_state = TextChoiceField(
        max_length=1, choices_cls=GradeStates, default=GradeStates.EMPTY
    )

    status = TextChoiceField(
        max_length=5, choices_cls=GradeStatuses, default=GradeStatuses.PENDING
    )


def gwa_sheet_file_path(instance, filename):
    file_ext = filename.split(".")[-1]
    file_name = str(uuid.uuid4()).replace("-", "")
    return f"gwa_sheets/{file_name}.{file_ext}"


class GeneralWeightedAverageSheet(BaseModel):
    class Statuses(models.TextChoices):
        PENDING = "P", "Pending"
        PROCESSING = "O", "Processing"
        FAILED = "F", "Failed"
        COMPLETED = "C", "Completed"

    HASHIDS = Hashids(
        settings.HASHIDS_GWA_SHEET_SALT,
        min_length=settings.HASHIDS_MIN_LENGTH,
        alphabet=settings.HASHIDS_ALPHABET_ALPHA_ONLY,
    )

    file_id = models.CharField(max_length=255, null=True)
    file = models.FileField(
        upload_to=gwa_sheet_file_path, validators=[csv_file_validator]
    )
    status = TextChoiceField(
        max_length=2, choices_cls=Statuses, default=Statuses.PENDING
    )
    error_message = models.TextField(blank=True)
    success = models.IntegerField(default=0, help_text="Successful entries")
    invalid = models.IntegerField(
        default=0, help_text="Entries with student IDs not found"
    )
    total = models.IntegerField(default=0, help_text="Total processed data")

    def __str__(self):
        return f"GWA Sheet {self.file_id}"

    def generate_id(self):
        self.file_id = self.HASHIDS.encode(self.id)
        self.save()


class StudentRequestTypes(models.TextChoices):
    CHANGE_SCHEDULE = "CS", "Change Schedule"
    OPEN_CLASS = "OC", "Open a Class"
    ADD_SUBJECT = "AS", "Add Subject"
    PARTIAL_WITHDRAWAL = "PW", "Partial Withdrawal"
    FULL_WITHDRAWAL = "FW", "Full Withdrawal"


class StudentRequest(PolymorphicBaseModel):
    HASHIDS = Hashids(
        settings.HASHIDS_STUDENT_REQUEST_SALT,
        min_length=settings.HASHIDS_MIN_LENGTH,
        alphabet=settings.HASHIDS_ALPHABET_ALPHA_ONLY,
    )

    student = models.ForeignKey(
        Student, on_delete=models.SET_NULL, null=True, related_name="requests"
    )

    request_no = models.CharField(max_length=255, null=True)
    detail = models.TextField(blank=False)
    reason = models.TextField(blank=False)

    def __str__(self):
        return f"{self.student} - Request {self.request_no}"

    def generate_request_no(self):
        self.request_no = self.HASHIDS.encode(self.id)
        self.save()


class ChangeScheduleRequest(StudentRequest):
    class Statuses(models.TextChoices):
        PENDING = "P", "Pending"
        INREVIEW = "IR", "In Review"
        APPROVED = "A", "Approved"
        REJECTED = "R", "Rejected"

    status = TextChoiceField(
        max_length=2, choices_cls=Statuses, default=Statuses.PENDING
    )

    def __str__(self):
        return f"{self.student} - Change Schedule Request {self.request_no}"


class AddSubjectRequest(StudentRequest):
    class Statuses(models.TextChoices):
        PENDING = "P", "Pending"
        INREVIEW = "IR", "In Review"
        APPROVED = "A", "Approved"
        REJECTED = "R", "Rejected"

    status = TextChoiceField(
        max_length=2, choices_cls=Statuses, default=Statuses.PENDING
    )

    def __str__(self):
        return f"{self.student} - Add Subject Request {self.request_no}"


class OpenClassRequest(StudentRequest):
    class Statuses(models.TextChoices):
        PENDING = "P", "Pending"
        FOR_APPROVAL = "FA", "For Approval"
        FOR_ENCODING = "FE", "For Encoding"
        ENCODED = "E", "Encoded"
        REJECTED = "R", "Rejected"

    status = TextChoiceField(
        max_length=2, choices_cls=Statuses, default=Statuses.PENDING
    )

    def __str__(self):
        return f"{self.student} - Open Class Request {self.request_no}"


class WithdrawalRequest(StudentRequest):
    class Statuses(models.TextChoices):
        PENDING = "P", "Pending"
        FOR_APPROVAL = "FA", "For Approval"
        FOR_ENCODING = "FE", "For Encoding"
        ENCODED = "E", "Encoded"
        REJECTED = "R", "Rejected"

    class Categories(models.TextChoices):
        FULL_WITHDRAWAL = "FW", "Full Withdrawal"
        PARTIAL_WITHDRAWAL = "PW", "Partial Withdrawal"

    class Types(models.TextChoices):
        PARTIAL_WITHIN_WITHDRAWAL_PERIOD = "PWWP", "Partial (Within Withdrawal Period)"
        PARTIAL_AFTER_WITHDRAWAL_PERIOD = "PAWP", "Partial (After Withdrawal Period)"
        FULL_WITHIN_FIRST_WEEK_WITHDRAWAL_PERIOD = (
            "FWFWWP",
            "Full (Within 1st Week Withdrawal Period)",
        )
        FULL_WITHIN_SECOND_WEEK_WITHDRAWAL_PERIOD = (
            "FWSWWP",
            "Full (Within 2nd Week Withdrawal Period)",
        )
        FULL_W_MEDCERT_WITHIN_PRELIM = (
            "FWMWP",
            "Full w/ Medical Certificate (Within Prelim Exams)",
        )
        FULL_W_MEDCERT_WITHIN_MIDTERM = (
            "FWMWM",
            "Full w/ Medical Certificate (Within Prelim Exams)",
        )
        FULL_AFTER_WITHDRAWAL_PERIOD = ("FAWP", "Full (After Withdrawal Period)")
        NO_CHARGE = ("NC", "No charge")

    status = TextChoiceField(
        max_length=2, choices_cls=Statuses, default=Statuses.PENDING
    )
    category = TextChoiceField(
        max_length=2, choices_cls=Categories, default=Categories.PARTIAL_WITHDRAWAL
    )
    type = TextChoiceField(max_length=8, choices_cls=Types, default=Types.NO_CHARGE)

    def __str__(self):
        return f"{self.student} - Withdrawal Request {self.request_no}"


class StudentRequestReviewHistory(BaseModel):
    request = models.ForeignKey(
        StudentRequest,
        on_delete=models.CASCADE,
        null=False,
        related_name="review_histories",
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="request_reviews",
    )

    remarks = models.TextField()
    status = models.CharField(max_length=255, blank=False, null=False)

    def __str__(self):
        return f"{self.id}"
