from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from university.core.accounts.models import AcademicYear, Module, School, Semester
from university.core.cms.models import Course
from university.core.students.models import Student
from university.framework.models import BaseModel, TextChoiceField


class ModuleConfiguration(BaseModel):
    module = models.OneToOneField(Module, on_delete=models.PROTECT)
    description = models.TextField()

    def __str__(self):
        return str(self.module)


class EnrollmentSchedule(BaseModel):
    class Statuses(models.TextChoices):
        ACTIVE = "A", "Active"
        SCHEDULED = "S", "Scheduled"
        ENDED = "E", "Ended"

    config = models.ForeignKey(
        ModuleConfiguration,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="enrollment_schedules",
    )
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="enrollment_schedules",
        blank=True,
        null=True,
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollment_schedules",
        blank=True,
        null=True,
    )

    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        related_name="enrollment_schedules",
        blank=True,
        null=True,
    )

    semester = models.ForeignKey(
        Semester,
        on_delete=models.CASCADE,
        related_name="enrollment_schedules",
        blank=True,
        null=True,
    )

    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    student_type = TextChoiceField(
        max_length=2, choices_cls=Student.Statuses, blank=True
    )
    year_level = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(4)]
    )

    def __str__(self):
        school_course = f"{self.school or 'All School'} - {self.course or 'All Course'}"
        return f"{self.config} - {self.school_year} - {self.semester} - {school_course}"

    @property
    def school_year(self) -> str:
        return f"{self.school_year_from}-{self.school_year_to}"

    @property
    def status(self) -> Statuses:
        now = timezone.now()

        if self.start_datetime <= now <= self.end_datetime:
            return self.Statuses.ACTIVE
        elif now < self.start_datetime:
            return self.Statuses.SCHEDULED
        elif now > self.end_datetime:
            return self.Statuses.ENDED


class EnrollmentScheduleEvent(BaseModel):
    schedule = models.ForeignKey(
        EnrollmentSchedule, on_delete=models.CASCADE, related_name="events"
    )
    event = models.CharField(max_length=255)
    tag = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.event
