from datetime import date

from django.conf import settings
from django.contrib.auth.models import (
    AbstractUser,
    Group,
    GroupManager,
    Permission,
    UserManager,
)
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Q
from django.forms.models import model_to_dict

from university.framework.models import (
    BaseModel,
    BaseModelMixin,
    SoftDeleteManager,
    SoftDeleteMixin,
    SoftDeleteModel,
    TextChoiceField,
)


class User(SoftDeleteMixin, AbstractUser):
    class Types(models.TextChoices):
        ADMIN = "A", "Admin"
        STUDENT = "S", "Student"
        NONE = "N", "None"

    class Status(models.TextChoices):
        ACTIVE = "a", "Active"
        LOCKED = "l", "Locked"

    status = TextChoiceField(max_length=2, choices_cls=Status, default=Status.ACTIVE)
    is_first_login = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    deleted_at = models.DateTimeField(
        null=True, blank=True, default=None, db_index=True
    )

    objects = UserManager()
    active_objects = SoftDeleteManager()

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def permissions(self) -> list[str]:
        return list(set([item for item in self.get_group_permissions()]))

    @property
    def type(self):
        try:
            self.student
            return self.Types.STUDENT
        except ObjectDoesNotExist:
            pass

        try:
            if self.personnel and self.is_staff:
                return self.Types.ADMIN
        except ObjectDoesNotExist:
            pass

        return self.Types.NONE

    def get_profile(self):
        if self.type == self.Types.ADMIN:
            return self.personnel
        elif self.type == self.Types.STUDENT:
            return self.student

        return self

    def to_dict(self, exclude=None, **kwargs):
        always_exclude = ["passwords"]
        if exclude:
            always_exclude += exclude
        return model_to_dict(self, exclude=always_exclude, **kwargs)

    def get_password_rem_days(self):
        """Computes the remaining days before password expiration"""

        last_password_update = (
            self.password_histories.all().order_by("-created_at").first()
        )
        if last_password_update:
            return settings.PASSWORD_DURATION - (
                abs((date.today() - last_password_update.created_at.date()).days)
            )
        return 0


class PasswordHistory(BaseModel):
    class Types(models.TextChoices):
        CHANGED = "C", "Changed"
        WAIVED = "W", "Waived"

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="password_histories"
    )
    type = TextChoiceField(max_length=2, choices_cls=Types, default=Types.CHANGED)
    value = models.CharField(max_length=128, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Password Histories"


class AdminRoleManager(GroupManager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(~Q(name__startswith=f"{settings.UNIVERSITY_CORE_RESERVED_ROLE_PREFIX}."))
        )


class Role(BaseModelMixin, Group):
    objects = GroupManager()
    admin_objects = AdminRoleManager()

    class Meta:
        proxy = True


class Module(BaseModel):
    class Platforms(models.TextChoices):
        WEB = "W", "Web"
        MOBILE = "M", "Mobile"

    class Categories(models.TextChoices):
        BASE = "B", "Base"
        DASHBOARD = "DB", "Dashboard"
        CMS = "CMS", "CMS"
        CONFIGURATION = "CON", "Configuration"
        TRANSACTION = "T", "Transaction"
        STUDENT_REQUEST = "ST", "Student Request"
        MOBILE = "M", "Mobile"

    name = models.CharField(max_length=255)
    sub_name = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    codename = models.CharField(max_length=255)

    roles = models.ManyToManyField(
        Group,
        through="RoleModule",
        through_fields=("module", "role"),
        related_name="modules",
    )
    users = models.ManyToManyField(User, related_name="modules")

    add_permissions = models.ManyToManyField(
        Permission, related_name="modules_add", blank=True
    )
    view_permissions = models.ManyToManyField(
        Permission, related_name="modules_view", blank=True
    )
    change_permissions = models.ManyToManyField(
        Permission, related_name="modules_change", blank=True
    )
    delete_permissions = models.ManyToManyField(
        Permission, related_name="modules_delete", blank=True
    )

    platform = TextChoiceField(max_length=2, choices_cls=Platforms)
    category = TextChoiceField(
        max_length=5, choices_cls=Categories, default=Categories.BASE
    )
    order = models.IntegerField(default=0, help_text="Sort index")

    def __str__(self):
        if self.sub_name:
            return f"{self.name} - {self.sub_name}"
        return self.name


class RoleModule(BaseModel):
    role = models.ForeignKey(Group, on_delete=models.CASCADE)
    module = models.ForeignKey(Module, on_delete=models.CASCADE)

    has_view_perm = models.BooleanField(default=False)
    has_add_perm = models.BooleanField(default=False)
    has_change_perm = models.BooleanField(default=False)
    has_delete_perm = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.role} - {self.module}"


class School(SoftDeleteModel):
    ref_id = models.CharField(max_length=50)
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=250)
    dean = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="dean_schools",
        blank=True,
        null=True,
    )

    def __str__(self):
        return f"{self.code} - {self.name}"


class UserSchoolGroup(BaseModel):
    school = models.ForeignKey(
        "school", on_delete=models.CASCADE, related_name="group_users"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="school_groups"
    )
    roles = models.ManyToManyField(Group)

    def __str__(self):
        return f"{self.user.username} {self.school.name}"

    def get_role_modules(self):
        from .selectors import school_group_role_modules_data_get

        return school_group_role_modules_data_get(school_group=self)


class Department(SoftDeleteModel):
    class DivisionGroups(models.TextChoices):
        TERTIARY = "1", "Tertiary"
        HOSPITAL = "2", "Hospital"
        ELEMENTARY = "3", "Elementary"
        HIGHSCHOOL = "4", "High School"

    school = models.ForeignKey(
        School,
        on_delete=models.SET_NULL,
        related_name="school_departments",
        blank=True,
        null=True,
    )

    department_head = models.ForeignKey(
        "Personnel",
        on_delete=models.SET_NULL,
        related_name="department_heads",
        blank=True,
        null=True,
    )

    main_department = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="main_departments",
        blank=True,
        null=True,
    )

    users = models.ManyToManyField(User, related_name="departments", blank=True)

    ref_id = models.CharField(max_length=50, db_index=True)
    code = models.CharField(max_length=50, db_index=True)
    name = models.CharField(max_length=250)
    division_group = TextChoiceField(
        max_length=20, choices_cls=DivisionGroups, default=DivisionGroups.TERTIARY
    )

    def __str__(self):
        return self.name


class Religion(BaseModel):
    code = models.CharField(max_length=50)
    description = models.TextField()

    def __str__(self):
        return self.code


class Personnel(SoftDeleteModel):
    class Genders(models.TextChoices):
        MALE = "M", "Male"
        FEMALE = "F", "Female"

    class CivilStatuses(models.TextChoices):
        SINGLE = "S", "Single"
        MARRIED = "M", "Married"
        WIDOWED = "W", "Widowed"

    class Nationalities(models.TextChoices):
        FILIPINO = "F", "Filipino"

    class UnionAffiliations(models.TextChoices):
        ELP = "E", "ELP"
        FACULTY_UNION = "U", "Faculty Union"
        ALLIANCE = "A", "ALLIANCE"

    class EmploymentTypes(models.TextChoices):
        FULL_TIME = "F", "Full-Time"
        PART_TIME = "P", "Part-Time"

    class Tenures(models.TextChoices):
        CASUAL = "A", "Casual"
        CONTRACTUAL = "C", "Contractual"
        REGULAR = "E", "Regular"
        STUDY_LEAVE = "L", "Study Leave"
        PART_TIME = "O", "Part-Time"
        PERMANENT = "P", "Permanent"
        PROBATIONARY = "R", "Probationary"
        SABBATICAL = "S", "Sabbatical"
        UNKNOWN = "U", "Unknown"

    class EmploymentStatuses(models.TextChoices):
        RESIGNED = "R", "Resigned"
        TERMINATED = "T", "Terminated"
        END_OF_CONTRACT = "C", "End of Contract"
        RETIRED = "E", "Retired"
        DESEASED = "D", "Deceased"
        NO_LOAD = "N", "No Load"
        RETRENCHED = "X", "Retrenched"

    class Ranks(models.TextChoices):
        OFFICER = "O", "Officer"
        SUPERVISOR = "S", "Supervisor"
        MANAGER = "M", "Manager"

    class Categories(models.TextChoices):
        FACULTY = "FE", "Faculty"
        CONTRACTUAL_FACULTY = "CF", "Contractual Faculty"
        ADMIN_EMPLOYEE = "AE", "Admin Employee"
        CONTRACTUAL_EMPLOYEE = "CE", "Contractual Employee"
        VISITING_LECTURER = "NS", "Visiting Lecturer"

    user = models.OneToOneField(User, on_delete=models.SET_NULL, blank=True, null=True)

    emp_id = models.CharField(max_length=50, db_index=True)
    ref_id = models.CharField(max_length=50, db_index=True, blank=True, null=True)
    old_id = models.CharField(max_length=50, blank=True, null=True)

    first_name = models.CharField(max_length=255, db_index=True)
    middle_name = models.CharField(max_length=255, db_index=True, blank=True, null=True)
    maiden_name = models.CharField(max_length=255, db_index=True, blank=True, null=True)
    last_name = models.CharField(max_length=255, db_index=True)

    birth_date = models.DateField(blank=True, null=True)
    birth_place = models.CharField(max_length=255, blank=True, null=True)
    gender = TextChoiceField(max_length=1, choices_cls=Genders, blank=True, null=True)

    civil_status = TextChoiceField(
        max_length=50, choices_cls=CivilStatuses, blank=True, null=True
    )
    nationality = TextChoiceField(
        max_length=50, choices_cls=Nationalities, blank=True, null=True
    )
    rank = TextChoiceField(max_length=50, choices_cls=Ranks, blank=True, null=True)
    category = TextChoiceField(max_length=50, choices_cls=Categories)

    spouse_name = models.CharField(max_length=250, blank=True, null=True)
    spouse_occupation = models.CharField(max_length=250, blank=True, null=True)
    no_of_child = models.IntegerField(default=0)

    religion = models.ForeignKey(
        Religion,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="personnel",
    )

    sss_no = models.CharField(max_length=255, blank=True, null=True)
    tin = models.CharField(max_length=255, blank=True, null=True)
    license_no = models.CharField(max_length=255, blank=True, null=True)
    pagibig_no = models.CharField(max_length=255, blank=True, null=True)
    philhealth_no = models.CharField(max_length=255, blank=True, null=True)

    phone_no = models.CharField(max_length=50, blank=True, null=True)
    home_phone_no = models.CharField(max_length=50, blank=True, null=True)
    local_address = models.CharField(max_length=250, blank=True, null=True)
    local_phone_no = models.CharField(max_length=250, blank=True, null=True)
    street = models.CharField(max_length=250, blank=True, null=True)
    barangay = models.CharField(max_length=250, blank=True, null=True)
    city = models.CharField(max_length=250, blank=True, null=True)
    zip_code = models.CharField(max_length=250, blank=True, null=True)

    relative_name = models.CharField(max_length=250, blank=True, null=True)
    relative_relationship = models.CharField(max_length=250, blank=True, null=True)
    relative_address = models.CharField(max_length=250, blank=True, null=True)
    relative_phone_no = models.CharField(max_length=250, blank=True, null=True)

    union_affiliation = TextChoiceField(
        max_length=50, choices_cls=UnionAffiliations, blank=True, null=True
    )
    employment_type = TextChoiceField(
        max_length=50, choices_cls=EmploymentTypes, blank=True, null=True
    )
    tenure = TextChoiceField(max_length=50, choices_cls=Tenures, blank=True, null=True)
    employee_status = TextChoiceField(
        max_length=50, choices_cls=EmploymentStatuses, blank=True, null=True
    )

    father_name = models.CharField(max_length=250, blank=True, null=True)
    mother_name = models.CharField(max_length=250, blank=True, null=True)
    marriage_date = models.DateField(blank=True, null=True)
    separation_date = models.DateField(blank=True, null=True)

    employment_date = models.DateField(blank=True, null=True)

    def __str__(self):
        s = f"{self.user.username} - {self.last_name}, {self.first_name}"
        if self.middle_name:
            s = f"{s} {self.middle_name}"
        return s

    @property
    def address(self):
        return f"{self.street} {self.barangay} {self.city}"

    @property
    def fullname(self):
        s = f"{self.first_name} {self.last_name}"
        if self.middle_name:
            s = f"{self.first_name} {self.middle_name} {self.last_name} "
        return s


class AcademicYear(SoftDeleteModel):
    year_start = models.PositiveIntegerField()
    year_end = models.PositiveIntegerField()
    date_start = models.DateField(blank=True, null=True)
    date_end = models.DateField(blank=True, null=True)
    id_start = models.PositiveIntegerField(blank=True, null=True)

    def __str__(self):
        return f"AY {self.year_start}-{self.year_end}"


class Semester(SoftDeleteModel):
    class Terms(models.TextChoices):
        FIRST_SEMESTER = "FS", "First Semester"
        SECOND_SEMESTER = "SS", "Second Semester"
        SUMMER = "S", "Summer"

    academic_year = models.ForeignKey(
        "AcademicYear",
        on_delete=models.CASCADE,
        related_name="semesters",
    )
    term = TextChoiceField(max_length=50, choices_cls=Terms)

    date_start = models.DateField(blank=True, null=True)
    date_end = models.DateField(blank=True, null=True)

    prelim_date_start = models.DateField(blank=True, null=True)
    prelim_date_end = models.DateField(blank=True, null=True)

    midterm_date_start = models.DateField(blank=True, null=True)
    midterm_date_end = models.DateField(blank=True, null=True)

    final_date_start = models.DateField(blank=True, null=True)
    final_date_end = models.DateField(blank=True, null=True)

    order = models.IntegerField()

    def __str__(self):
        return f"AY {self.academic_year.year_start}-{self.academic_year.year_end} | {self.term}"
