from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Count
from django.db.models.functions import TruncDate
from rest_framework import serializers

from university.core.accounts.models import AcademicYear, School, Semester
from university.core.accounts.selectors import current_semester_get, next_semester_get
from university.core.cms.models import (
    Building,
    Class,
    ClassSchedule,
    Course,
    Curriculum,
    CurriculumPeriod,
    CurriculumSubject,
    Discount,
    Room,
    Subject,
)
from university.core.cms.serializers import ClassSerializer, CourseBaseSerializer
from university.framework.serializers import ChoiceField, inline_serializer_class
from university.payment.serializers import StatementOfAccountSerializer

from . import models, selectors

User = get_user_model()


def curriculum_subject_is_completed(serializer, obj):
    enrollment = serializer.context.get("enrollment")

    if not enrollment:
        return None

    return selectors.enrollment_curriculum_subject_is_completed(
        enrollment=enrollment, curriculum_subject=obj
    )


def curriculum_period_total_units(serializer, obj):
    enrollment = serializer.context.get("enrollment")

    if not enrollment:
        return None

    return selectors.enrollment_total_units_get(enrollment=enrollment)


class StudentProfileRetrieveSerializer(serializers.ModelSerializer):
    CourseSerializer = inline_serializer_class(
        model=Course, fields=("code", "sub_code", "name")
    )

    AcademicYearSerializer = inline_serializer_class(
        model=AcademicYear,
        fields=("id", "year_start", "year_end", "date_start", "date_end"),
    )

    SemesterSerializer = inline_serializer_class(
        model=Semester,
        fields=("academic_year", "id", "term", "date_start", "date_end", "order"),
        declared_fields={"academic_year": AcademicYearSerializer()},
    )

    semester = SemesterSerializer()
    course = serializers.SerializerMethodField()
    total_units = serializers.SerializerMethodField()

    class Meta:
        model = models.Student
        fields = (
            "id_number",
            "first_name",
            "middle_name",
            "last_name",
            "gender",
            "civil_status",
            "birth_date",
            "birth_place",
            "religion",
            "citizenship",
            "nationality",
            "email",
            "phone_no",
            "address",
            "province",
            "city",
            "barangay",
            "street",
            "zip_code",
            "home_phone_no",
            "local_address",
            "local_phone_no",
            "father_name",
            "father_occupation",
            "mother_name",
            "mother_occupation",
            "guardian_name",
            "guardian_address",
            "emergency_contact_name",
            "emergency_contact_address",
            "emergency_contact_email",
            "emergency_contact_phone_no",
            "course",
            "semester",
            "year_level",
            "total_units",
            "birth_date",
            "institutional_email",
        )

    def get_course(self, obj) -> CourseSerializer:
        course = selectors.student_course_get(user=obj.user)
        if course:
            return self.CourseSerializer(course).data

    def get_total_units(self, obj) -> Decimal:
        return selectors.enrollment_latest_enrolled_total_units_get(user=obj.user)


class StudentProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Student
        fields = (
            "gender",
            "civil_status",
            "birth_date",
            "birth_place",
            "religion",
            "citizenship",
            "nationality",
            "email",
            "phone_no",
            "province",
            "city",
            "barangay",
            "street",
            "zip_code",
            "home_phone_no",
            "local_address",
            "local_phone_no",
            "father_name",
            "father_occupation",
            "mother_name",
            "mother_occupation",
            "guardian_name",
            "guardian_address",
            "emergency_contact_name",
            "emergency_contact_address",
            "emergency_contact_email",
            "emergency_contact_phone_no",
        )


class StudentListSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Student
        fields = (
            "id",
            "id_number",
            "first_name",
            "middle_name",
            "last_name",
            "birth_date",
        )


class ClassGradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.EnrolledClassGrade
        fields = (
            "prelim_grade",
            "midterm_grade",
            "tentative_final_grade",
            "final_grade",
            "final_status",
            "remarks",
        )


class StudentGradeScheduleRetrieveSubSerializer(serializers.ModelSerializer):
    grades = serializers.SerializerMethodField()
    subject_class = ClassSerializer()

    class Meta:
        model = models.EnrolledClass
        fields = "__all__"

    def get_grade(self, obj):
        if hasattr(obj, "grades"):
            return ClassGradeSerializer(obj.grades).data
        return None


class StudentRetrieveSerializer(serializers.ModelSerializer):
    AcademicYearSerializer = inline_serializer_class(
        model=AcademicYear,
        fields=("id", "year_start", "year_end", "date_start", "date_end"),
    )

    SemesterSerializer = inline_serializer_class(
        model=Semester,
        fields=("academic_year", "id", "term", "date_start", "date_end", "order"),
        declared_fields={"academic_year": AcademicYearSerializer()},
    )

    semester = SemesterSerializer()
    course = serializers.SerializerMethodField()
    total_units = serializers.SerializerMethodField()

    class Meta:
        model = models.Student
        fields = "__all__"

    def get_course(self, obj) -> CourseBaseSerializer:
        course = selectors.student_course_get(user=obj.user)
        if course:
            return CourseBaseSerializer(course).data

    def get_total_units(self, obj) -> Decimal:
        return selectors.enrollment_latest_enrolled_total_units_get(user=obj.user)


class EnrollmentSubjectScheduleSerializer(serializers.ModelSerializer):
    klass = ClassSerializer()

    class Meta:
        model = models.EnrolledClass
        fields = "__all__"


class EnrollmentRetrieveSerializer(serializers.ModelSerializer):
    DiscountSerializer = inline_serializer_class(
        model=Discount, fields=("type", "name", "percentage")
    )

    UserSerializer = inline_serializer_class(model=models.User, fields=("username",))

    PersonnelSerializer = inline_serializer_class(
        model=models.Personnel,
        fields=("user", "first_name", "last_name"),
        declared_fields={"user": UserSerializer()},
    )

    StudentSerializer = inline_serializer_class(
        model=models.Student, fields=("id_number", "first_name", "last_name")
    )

    EnrollmentDiscountSerializer = inline_serializer_class(
        model=models.EnrollmentDiscount,
        fields=(
            "is_employee",
            "personnel",
            "is_employee_dependent",
            "dependent_personnel",
            "dependent_relationship",
            "is_working_scholar",
            "has_enrolled_sibling",
            "siblings",
        ),
        declared_fields={
            "siblings": StudentSerializer(many=True),
            "personnel": PersonnelSerializer(),
            "dependent_personnel": PersonnelSerializer(),
        },
    )

    EnrollmentStatusSerializer = inline_serializer_class(
        model=models.EnrollmentStatus,
        fields=(
            "block_status",
            "is_for_manual_tagging",
            "is_temporary_allowed",
            "evaluation_remarks",
            "remark_code",
        ),
    )

    AcademicYearSerializer = inline_serializer_class(
        model=AcademicYear,
        fields=("id", "year_start", "year_end", "date_start", "date_end"),
    )

    SemesterSerializer = inline_serializer_class(
        model=Semester,
        fields=("academic_year", "id", "term", "date_start", "date_end", "order"),
        declared_fields={"academic_year": AcademicYearSerializer()},
    )

    semester = SemesterSerializer()
    enrolled_classes = EnrollmentSubjectScheduleSerializer(many=True)
    statement_of_account = StatementOfAccountSerializer()
    discount = serializers.SerializerMethodField()
    enrollment_status = serializers.SerializerMethodField()
    max_units = serializers.SerializerMethodField()

    class Meta:
        model = models.Enrollment
        fields = "__all__"

    def get_discount(self, obj) -> DiscountSerializer:
        if hasattr(obj, "discounts"):
            return self.EnrollmentDiscountSerializer(obj.discounts).data
        return None

    def get_enrollment_status(self, obj) -> EnrollmentStatusSerializer:
        if hasattr(obj, "enrollmentstatus"):
            return self.EnrollmentStatusSerializer(obj.enrollmentstatus).data
        return None

    def get_max_units(self, obj) -> Decimal:
        semester = next_semester_get()

        if not semester:
            return 0

        curr_period = obj.student.curriculum.curriculum_periods.filter(
            semester=semester.term, year_level=obj.year_level
        ).first()
        return curr_period.get_total_units() or 0


class EnrollmentDefaultUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Enrollment
        fields = ("step",)


class EnrollmentInformationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Enrollment
        fields = (
            "id",
            "current_address",
            "contact_number",
            "personal_email",
            "institutional_email",
            "father_name",
            "father_occupation",
            "mother_name",
            "mother_occupation",
            "is_living_with_parents",
            "emergency_contact_name",
            "emergency_contact_address",
            "emergency_contact_phone_no",
            "emergency_contact_email",
            "step",
        )


class EnrollmentDiscountSerializer(serializers.ModelSerializer):
    sibling_student_numbers = serializers.ListField(
        child=serializers.CharField(), write_only=True
    )
    step = serializers.ChoiceField(choices=models.Enrollment.Steps)
    employee_no = serializers.CharField(
        max_length=6, min_length=6, allow_blank=True, write_only=True
    )
    dependent_employee_no = serializers.CharField(
        max_length=6, min_length=6, allow_blank=True, write_only=True
    )

    class Meta:
        model = models.EnrollmentDiscount
        fields = (
            "is_employee",
            "employee_no",
            "is_employee_dependent",
            "dependent_employee_no",
            "dependent_relationship",
            "is_working_scholar",
            "has_enrolled_sibling",
            "sibling_student_numbers",
            "step",
        )

    def validate_employee_no(self, employee_no):
        if employee_no and not User.objects.filter(username=employee_no):
            raise serializers.ValidationError(
                f"Invalid Employee ID Number: {employee_no}"
            )
        return employee_no

    def validate_sibling_student_numbers(self, sibling_student_numbers):
        for student_no in sibling_student_numbers:
            if not User.objects.filter(username=student_no):
                raise serializers.ValidationError(
                    f"Invalid Student Number: {student_no}"
                )

        return sibling_student_numbers

    def validate_dependent_employee_no(self, dependent_employee_no):
        if dependent_employee_no and not User.objects.filter(
            username=dependent_employee_no
        ):
            raise serializers.ValidationError(
                f"Invalid Employee ID Number: {dependent_employee_no}"
            )
        return dependent_employee_no

    def validate(self, data):
        if data.get("is_employee"):
            if not data.get("employee_no"):
                raise serializers.ValidationError(
                    "Employee ID Number can't be null value."
                )

        if data.get("is_employee_dependent", None):
            if not data.get("dependent_employee_no"):
                raise serializers.ValidationError(
                    "Dependent Employee ID Number can't be null value."
                )

        if data.get("has_enrolled_sibling", None):
            if not data.get("sibling_student_numbers"):
                raise serializers.ValidationError(
                    "Atleast 1 student number is required"
                )

        return data


class EnrolledClassSerializer(serializers.Serializer):
    EnrolledClassSerializer = inline_serializer_class(
        model=models.EnrolledClass,
        fields=("klass", "curriculum_subject"),
        declared_fields={},
    )

    step = serializers.ChoiceField(choices=models.Enrollment.Steps)
    enrolled_classes = EnrolledClassSerializer(many=True)

    def validate(self, data):
        for klass in data.get("enrolled_classes"):
            if not klass.get("klass").has_available_slot_for_reservation():
                raise serializers.ValidationError("Class has no available slot.")

        return data


class EnrollmentSubjectScheduleRetrieveSerializer(serializers.ModelSerializer):
    subject_class = ClassSerializer()
    grades = ClassGradeSerializer()

    class Meta:
        model = models.EnrolledClass
        fields = "__all__"


class CurriculumPeriodSubSerializer(serializers.ModelSerializer):
    total_units = serializers.DecimalField(
        source="get_total_units", max_digits=9, decimal_places=2
    )
    total_units_passed = serializers.SerializerMethodField()
    total_units_failed = serializers.SerializerMethodField()

    class Meta:
        model = CurriculumPeriod
        fields = (
            "semester",
            "year_level",
            "total_units",
            "total_units_passed",
            "total_units_failed",
        )

    def get_enrollment(self, obj):
        enrollment = self.context.get("enrollment")
        if enrollment:
            return enrollment
        return False

    def get_total_units_passed(self, obj) -> int:
        enrollment = self.get_enrollment(obj)

        if enrollment:
            return selectors.student_enrollment_passed_units_get(enrollment=enrollment)

    def get_total_units_failed(self, obj) -> int:
        enrollment = self.get_enrollment(obj)

        if enrollment:
            return selectors.student_enrollment_failed_units_get(enrollment=enrollment)


class EnrollmentSerializer(serializers.ModelSerializer):
    enrolled_classes = EnrollmentSubjectScheduleRetrieveSerializer(many=True)
    curriculum_period = serializers.SerializerMethodField()

    class Meta:
        model = models.Enrollment
        fields = "__all__"

    def get_curriculum_period(self, obj):
        return CurriculumPeriodSubSerializer(
            obj.curriculum_period, context={"enrollment": obj}
        ).data


class EnrollmentSubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ("course_number", "descriptive_title", "units", "no_of_hours")


class EnrollmentCurriculumSubjectListSerializer(serializers.ModelSerializer):
    subject = EnrollmentSubjectSerializer()
    is_completed = serializers.SerializerMethodField()

    class Meta:
        model = CurriculumSubject
        fields = ("subject", "is_completed")

    def get_is_completed(self, obj) -> bool | None:
        enrollment = self.context.get("enrollment")
        if not enrollment:
            return None
        return selectors.enrollment_curriculum_subject_is_completed(
            enrollment=enrollment, curriculum_subject=obj
        )


class EnrollmentCurriculumPeriodListSerializer(serializers.ModelSerializer):
    curriculum_subjects = serializers.SerializerMethodField()

    class Meta:
        model = CurriculumPeriod
        fields = ("semester", "year_level", "curriculum_subjects")

    def get_curriculum_subjects(self, obj) -> EnrollmentCurriculumSubjectListSerializer(
        many=True
    ):
        return EnrollmentCurriculumSubjectListSerializer(
            obj.subjects.all(), many=True, context=self.context
        ).data


class EnrollmentListSerializer(serializers.ModelSerializer):
    curriculum_period = serializers.SerializerMethodField()

    class Meta:
        model = models.Enrollment
        fields = ("curriculum_period",)

    def get_curriculum_period(self, obj) -> EnrollmentCurriculumPeriodListSerializer:
        return EnrollmentCurriculumPeriodListSerializer(
            obj.curriculum_period, context={"enrollment": obj}
        ).data


class StudentClassGradeRetrieveSerializer(serializers.ModelSerializer):
    enrollments = EnrollmentSerializer(many=True)

    class Meta:
        model = models.Student
        fields = (
            "id",
            "id_number",
            "first_name",
            "middle_name",
            "last_name",
            "birth_date",
            "enrollments",
        )


class EnrollmentSubjectScheduleRetrieveSubSerializer(serializers.ModelSerializer):
    grades = ClassGradeSerializer()
    student = serializers.SerializerMethodField()

    class Meta:
        model = models.EnrolledClass
        fields = "__all__"

    def get_student(self, obj) -> models.Student:
        return StudentListSerializer(obj.enrollment.student).data


class StudentGradeScheduleRetrieveSubSerializer(serializers.ModelSerializer):
    grades = ClassGradeSerializer()
    klass = ClassSerializer()

    class Meta:
        model = models.EnrolledClass
        fields = "__all__"


class EnrollmentRemarkUpdateSerializer(serializers.Serializer):
    enrollment_ids = serializers.ListField(child=serializers.IntegerField())
    remark_code = serializers.ChoiceField(choices=models.EnrollmentStatus.RemarkCodes)
    evaluation_remarks = serializers.CharField()


class EnrollmentStatusUpdateSerializer(serializers.Serializer):
    enrollment_ids = serializers.ListField(child=serializers.IntegerField())
    status = serializers.ChoiceField(choices=models.Enrollment.Statuses)
    is_temporary_allowed = serializers.BooleanField(default=False)


class EnrollmentStudentBaseSerializer(serializers.ModelSerializer):
    school = serializers.SerializerMethodField()
    course = serializers.SerializerMethodField()

    class Meta:
        model = models.Student
        fields = (
            "id",
            "id_number",
            "first_name",
            "last_name",
            "school",
            "year_level",
            "semester",
            "course",
        )

    def get_school(self, obj) -> str:
        return obj.course.school.name if obj.course else None

    def get_course(self, obj) -> str:
        return obj.course.name if obj.course else None


class EnrollmentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.EnrollmentStatus
        fields = (
            "block_status",
            "is_for_manual_tagging",
            "is_temporary_allowed",
            "evaluation_remarks",
            "remark_code",
        )


class EnrollmentStudentSerializer(serializers.ModelSerializer):
    student = EnrollmentStudentBaseSerializer()
    enrollment_status = serializers.SerializerMethodField()

    class Meta:
        model = models.Enrollment
        fields = ("id", "student", "status", "enrollment_status")

    def get_enrollment_status(self, obj) -> EnrollmentStatusSerializer:
        if hasattr(obj, "enrollmentstatus"):
            return EnrollmentStatusSerializer(obj.enrollmentstatus).data
        return None


class StudentEnrollmentUpcomingSerializer(serializers.ModelSerializer):
    EnrollmentStatusSerializer = inline_serializer_class(
        model=models.EnrollmentStatus,
        fields=(
            "block_status",
            "is_for_manual_tagging",
            "is_temporary_allowed",
            "evaluation_remarks",
            "remark_code",
        ),
    )

    enrollment_status = serializers.SerializerMethodField()

    class Meta:
        model = models.Enrollment
        fields = ("id", "student", "status", "enrollment_status")

    def get_enrollment_status(self, obj) -> EnrollmentStatusSerializer:
        if hasattr(obj, "enrollmentstatus"):
            return EnrollmentStatusSerializer(obj.enrollmentstatus).data
        return None


class EnrollmentActiveRetrieveSerializer(serializers.ModelSerializer):
    DiscountSerializer = inline_serializer_class(
        model=Discount, fields=("type", "name", "percentage")
    )
    EnrollmentStatusSerializer = inline_serializer_class(
        model=models.EnrollmentStatus,
        fields=(
            "block_status",
            "is_for_manual_tagging",
            "is_temporary_allowed",
            "evaluation_remarks",
            "remark_code",
        ),
    )

    AcademicYearSerializer = inline_serializer_class(
        model=AcademicYear,
        fields=("id", "year_start", "year_end", "date_start", "date_end"),
    )

    SemesterSerializer = inline_serializer_class(
        model=Semester,
        fields=("academic_year", "id", "term", "date_start", "date_end", "order"),
        declared_fields={"academic_year": AcademicYearSerializer()},
    )

    semester = SemesterSerializer()
    enrolled_classes = EnrollmentSubjectScheduleSerializer(many=True)
    statement_of_account = StatementOfAccountSerializer()
    discount = serializers.SerializerMethodField()
    enrollment_status = serializers.SerializerMethodField()

    class Meta:
        model = models.Enrollment
        fields = "__all__"

    def get_discount(self, obj) -> DiscountSerializer:
        if obj.discount:
            return self.DiscountSerializer(obj.discount).data
        return None

    def get_enrollment_status(self, obj) -> EnrollmentStatusSerializer:
        if hasattr(obj, "enrollmentstatus"):
            return self.EnrollmentStatusSerializer(obj.enrollmentstatus).data
        return None


class StudentCurriculumSubjectSerializer(serializers.ModelSerializer):
    SubjectSerializer = inline_serializer_class(
        model=Subject,
        fields=(
            "course_code",
            "course_number",
            "descriptive_code",
            "descriptive_title",
            "units",
            "no_of_hours",
        ),
        declared_fields={},
    )

    CurriculumSubjectRequisiteSerializer = inline_serializer_class(
        model=CurriculumSubject,
        fields=("requisite_subject",),
        declared_fields={"requisite_subject": SubjectSerializer()},
    )

    subject = SubjectSerializer()
    requisites = CurriculumSubjectRequisiteSerializer(many=True)
    is_passed = serializers.SerializerMethodField()
    is_taken = serializers.SerializerMethodField()
    final_grade = serializers.SerializerMethodField()

    class Meta:
        model = CurriculumSubject
        fields = ("subject", "requisites", "is_passed", "is_taken", "final_grade")

    def get_is_passed(self, obj):
        curr_subj_ids = self.context["passed_curr_subj_ids"]
        return obj.id in curr_subj_ids

    def get_is_taken(self, obj):
        curr_subj_ids = self.context["curr_subj_ids"]
        return obj.id in curr_subj_ids

    def get_final_grade(self, obj):
        student = self.context["student"]
        enrolled_class = (
            student.enrolled_classes.filter(curriculum_subject=obj)
            .order_by("-created_at")
            .first()
        )
        if enrolled_class:
            return enrolled_class.grades.final_grade

        return None


class StudentCurriculumRetrieveSerializer(serializers.ModelSerializer):
    CourseSerializer = inline_serializer_class(
        model=Course, fields=("code", "sub_code", "name")
    )

    CurriculumPeriodSerializer = inline_serializer_class(
        model=CurriculumPeriod,
        fields=("semester", "year_level", "order", "curriculum_subjects"),
        declared_fields={
            "curriculum_subjects": StudentCurriculumSubjectSerializer(many=True)
        },
    )

    course = CourseSerializer()
    curriculum_periods = serializers.SerializerMethodField()

    class Meta:
        model = Curriculum
        fields = (
            "id",
            "effective_start_year",
            "effective_end_year",
            "course",
            "curriculum_periods",
        )

    def get_curriculum_periods(self, obj) -> CurriculumPeriodSerializer(many=True):
        curriculum_periods = obj.curriculum_periods.all().order_by(
            "year_level", "order"
        )
        return self.CurriculumPeriodSerializer(
            curriculum_periods,
            many=True,
            context={**self.context},
        ).data


class StudentEnrollmentListSerializer(serializers.ModelSerializer):
    DiscountSerializer = inline_serializer_class(
        model=Discount, fields=("type", "name", "percentage")
    )

    AcademicYearSerializer = inline_serializer_class(
        model=AcademicYear,
        fields=("id", "year_start", "year_end", "date_start", "date_end"),
    )

    SemesterSerializer = inline_serializer_class(
        model=Semester,
        fields=("academic_year", "id", "term", "date_start", "date_end", "order"),
        declared_fields={"academic_year": AcademicYearSerializer()},
    )

    SubjectSerializer = inline_serializer_class(
        model=Subject,
        fields=(
            "course_code",
            "course_number",
            "descriptive_code",
            "descriptive_title",
        ),
        declared_fields={},
    )

    CurriculumSubjectSerializer = inline_serializer_class(
        model=CurriculumSubject,
        fields=("subject", "requisites"),
        declared_fields={"subject": SubjectSerializer()},
    )

    RoomSerializer = inline_serializer_class(
        model=Room,
        fields=("number", "name"),
        declared_fields={},
    )

    ClassScheduleSerializer = inline_serializer_class(
        model=ClassSchedule,
        fields=(
            "room",
            "time_in",
            "time_out",
            "day",
        ),
        declared_fields={"room": RoomSerializer()},
    )

    ClassSerializer = inline_serializer_class(
        model=Class,
        fields=(
            "class_code",
            "class_schedules",
        ),
        declared_fields={
            "class_schedules": ClassScheduleSerializer(many=True),
        },
    )

    EnrolledClassSerializer = inline_serializer_class(
        model=models.EnrolledClass,
        fields=(
            "klass",
            "curriculum_subject",
            "equivalent_subject",
            "status",
        ),
        declared_fields={
            "curriculum_subject": CurriculumSubjectSerializer(),
            "equivalent_subject": SubjectSerializer(),
            "klass": ClassSerializer(),
        },
    )

    semester = SemesterSerializer()
    enrolled_classes = EnrolledClassSerializer(many=True)
    discount = serializers.SerializerMethodField()
    total_units = serializers.SerializerMethodField()

    class Meta:
        model = models.Enrollment
        fields = "__all__"

    def get_discount(self, obj) -> DiscountSerializer:
        if obj.discount:
            return self.DiscountSerializer(obj.discount).data
        return None

    def get_total_units(self, obj) -> Decimal:
        return selectors.enrollment_total_units_get(enrollment=obj)


class StudentEnrollmentClassGradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.EnrolledClassGrade
        fields = (
            "prelim_grade",
            "midterm_grade",
            "tentative_final_grade",
            "final_grade",
            "status",
        )


class StudentEnrollmentGradeListSerializer(serializers.ModelSerializer):
    AcademicYearSerializer = inline_serializer_class(
        model=AcademicYear,
        fields=("id", "year_start", "year_end"),
    )

    SemesterSerializer = inline_serializer_class(
        model=Semester,
        fields=("academic_year", "id", "term", "order"),
        declared_fields={"academic_year": AcademicYearSerializer()},
    )

    SubjectSerializer = inline_serializer_class(
        model=Subject,
        fields=(
            "course_code",
            "course_number",
            "descriptive_code",
            "descriptive_title",
            "units",
        ),
        declared_fields={},
    )

    CurriculumSubjectSerializer = inline_serializer_class(
        model=CurriculumSubject,
        fields=("subject",),
        declared_fields={"subject": SubjectSerializer()},
    )
    ClassSerializer = inline_serializer_class(
        model=Class,
        fields=("class_code",),
        declared_fields={},
    )

    EnrolledClassSerializer = inline_serializer_class(
        model=models.EnrolledClass,
        fields=(
            "klass",
            "curriculum_subject",
            "equivalent_subject",
            "status",
            "grades",
        ),
        declared_fields={
            "curriculum_subject": CurriculumSubjectSerializer(),
            "equivalent_subject": SubjectSerializer(),
            "grades": StudentEnrollmentClassGradeSerializer(),
            "klass": ClassSerializer(),
        },
    )

    semester = SemesterSerializer()
    enrolled_classes = serializers.SerializerMethodField()
    total_units = serializers.SerializerMethodField()

    class Meta:
        model = models.Enrollment
        fields = ("semester", "year_level", "total_units", "enrolled_classes")

    def get_total_units(self, obj) -> Decimal:
        return selectors.enrollment_total_units_get(enrollment=obj)

    def get_enrolled_classes(self, obj) -> EnrolledClassSerializer:
        enrolled_classes = obj.enrolled_classes.filter(
            status=models.EnrolledClass.Statuses.ENROLLED
        )
        return self.EnrolledClassSerializer(enrolled_classes, many=True).data


class EnrolledClassGradeListSerializer(serializers.ModelSerializer):
    CourseSerializer = inline_serializer_class(
        model=Course, fields=("code", "sub_code", "name")
    )

    StudentSerializer = inline_serializer_class(
        model=models.Student,
        fields=("id_number", "first_name", "last_name", "year_level", "course"),
        declared_fields={"course": CourseSerializer()},
    )

    GradeSerializer = inline_serializer_class(
        model=models.EnrolledClassGrade,
        fields=(
            "prelim_grade",
            "midterm_grade",
            "tentative_final_grade",
            "final_grade",
            "prelim_grade_state",
            "midterm_grade_state",
            "tentative_final_grade_state",
            "final_grade_state",
            "status",
            "remarks",
        ),
        declared_fields={},
    )

    student = serializers.SerializerMethodField()
    grades = serializers.SerializerMethodField()

    class Meta:
        model = models.EnrolledClass
        fields = ("id", "student", "grades")

    def get_student(self, obj) -> StudentSerializer:
        return self.StudentSerializer(obj.enrollment.student).data

    def get_grades(self, obj) -> GradeSerializer:
        return self.GradeSerializer(obj.grades).data


class StudentClassGradeListSerializer(serializers.ModelSerializer):
    AcademicYearSerializer = inline_serializer_class(
        model=AcademicYear,
        fields=("id", "year_start", "year_end"),
    )

    SemesterSerializer = inline_serializer_class(
        model=Semester,
        fields=("academic_year", "id", "term", "order"),
        declared_fields={"academic_year": AcademicYearSerializer()},
    )

    SubjectSerializer = inline_serializer_class(
        model=Subject,
        fields=(
            "course_code",
            "course_number",
            "descriptive_code",
            "descriptive_title",
            "units",
        ),
        declared_fields={},
    )

    ClassSerializer = inline_serializer_class(
        model=Class,
        fields=("subject",),
        declared_fields={"subject": SubjectSerializer()},
    )

    GradeSerializer = inline_serializer_class(
        model=models.EnrolledClassGrade,
        fields=(
            "prelim_grade",
            "midterm_grade",
            "tentative_final_grade",
            "final_grade",
            "prelim_grade_state",
            "midterm_grade_state",
            "tentative_final_grade_state",
            "final_grade_state",
            "status",
            "remarks",
        ),
        declared_fields={},
    )

    EnrolledClassSerializer = inline_serializer_class(
        model=models.EnrolledClass,
        fields=("klass", "grades"),
        declared_fields={"klass": ClassSerializer(), "grades": GradeSerializer()},
    )

    semester = SemesterSerializer()
    enrolled_classes = EnrolledClassSerializer(many=True)
    total_units = serializers.SerializerMethodField()

    class Meta:
        model = models.Enrollment
        fields = ("semester", "year_level", "total_units", "enrolled_classes")

    def get_total_units(self, obj) -> Decimal:
        return selectors.enrollment_latest_enrolled_total_units_get(
            user=obj.student.user
        )


class StudentClassListSerializer(serializers.ModelSerializer):
    SubjectSerializer = inline_serializer_class(
        model=Subject,
        fields=(
            "course_code",
            "course_number",
            "descriptive_code",
            "descriptive_title",
            "units",
        ),
        declared_fields={},
    )

    RoomSerializer = inline_serializer_class(
        model=Room,
        fields=("name", "number", "floor_no"),
        declared_fields={},
    )

    ClassScheduleSerializer = inline_serializer_class(
        model=ClassSchedule,
        fields=("ref_id", "time_in", "time_out", "day", "room"),
        declared_fields={"room": RoomSerializer()},
    )

    subject = SubjectSerializer()
    class_schedules = ClassScheduleSerializer(many=True)

    class Meta:
        model = Class
        fields = ("class_code", "subject", "class_schedules")


class FailedStudentPerSchoolSerializer(serializers.ModelSerializer):
    no_of_failed_students = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = ("code", "name", "no_of_failed_students")

    def get_no_of_failed_students(self, obj) -> int:
        year_level = self.context["year_level"]
        semester = current_semester_get()

        enrollments = models.Enrollment.objects.filter(
            semester=semester,
            student__course__school=obj,
            grade__grading_status=models.EnrollmentGrade.GradingStatuses.FAILED,
            enrollmentstatus__is_for_manual_tagging=False,
            enrollmentstatus__block_status=models.EnrollmentStatus.BlockStatuses.BLOCKED_WITH_FAILED_SUBJECT,
        )

        # TODO: Custom filterclass for year_level
        if year_level and year_level.isnumeric():
            enrollments = enrollments.filter(year_level=year_level)

        return enrollments.count()


class InterviewedFailedStudentPerSchoolSerializer(serializers.ModelSerializer):
    no_of_interviewed_students = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = ("code", "name", "no_of_interviewed_students")

    def get_no_of_interviewed_students(self, obj) -> int:
        year_level = self.context["year_level"]
        semester = current_semester_get()

        enrollments = models.Enrollment.objects.filter(
            semester=semester,
            student__course__school=obj,
            grade__grading_status=models.EnrollmentGrade.GradingStatuses.FAILED,
            enrollmentstatus__is_for_manual_tagging=True,
            enrollmentstatus__block_status=models.EnrollmentStatus.BlockStatuses.BLOCKED_WITH_FAILED_SUBJECT,
        )

        # TODO: Custom filterclass for year_level
        if year_level and year_level.isnumeric():
            enrollments = enrollments.filter(year_level=year_level)

        return enrollments.count()


class EnrolleesPerSchoolSerializer(serializers.ModelSerializer):
    no_of_enrollees = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = ("code", "name", "no_of_enrollees")

    def get_no_of_enrollees(self, obj) -> int:
        year_level = self.context["year_level"]
        semester = current_semester_get()

        enrollments = models.Enrollment.objects.filter(
            semester=semester, student__course__school=obj
        )

        # TODO: Custom filterclass for year_level
        if year_level and year_level.isnumeric():
            enrollments = enrollments.filter(year_level=year_level)

        return enrollments.count()


class GradeSheetDetailApiSerializer(serializers.ModelSerializer):
    StudentSerializer = inline_serializer_class(
        model=models.Student,
        fields=("id_number", "name"),
        name=serializers.SerializerMethodField(),
        get_name=lambda _, obj: f"{obj.first_name} {obj.last_name}",
    )
    GradeSheetRowSerializer = inline_serializer_class(
        model=models.GradeSheetRow,
        fields=(
            "student",
            "prelim_grade",
            "midterm_grade",
            "tentative_final_grade",
            "final_grade",
            "prelim_grade_state",
            "midterm_grade_state",
            "tentative_final_grade_state",
            "final_grade_state",
            "status",
        ),
        student=StudentSerializer(),
    )

    rows = GradeSheetRowSerializer(many=True)

    class Meta:
        model = models.GradeSheet
        fields = ("file_id", "klass", "status", "error_message", "rows")


class EnrolleeScholarPerSchoolSerializer(serializers.ModelSerializer):
    no_of_regular = serializers.SerializerMethodField()
    no_of_scholar = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = ("code", "name", "no_of_scholar", "no_of_regular")

    def get_no_of_scholar(self, obj) -> int:
        year_level = self.context["year_level"]
        semester = current_semester_get()

        enrollments = models.Enrollment.objects.filter(
            semester=semester, student__course__school=obj, discount__isnull=False
        )

        # TODO: Custom filterclass for year_level
        if year_level and year_level.isnumeric():
            enrollments = enrollments.filter(year_level=year_level)

        return enrollments.count()

    def get_no_of_regular(self, obj) -> int:
        year_level = self.context["year_level"]
        semester = current_semester_get()

        enrollments = models.Enrollment.objects.filter(
            semester=semester, student__course__school=obj
        )

        # TODO: Custom filterclass for year_level
        if year_level and year_level.isnumeric():
            enrollments = enrollments.filter(year_level=year_level)

        return enrollments.count()


class EnrollmentGWAUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.GeneralWeightedAverageSheet
        fields = ("file",)


class EnrolleesPerDayPerSchoolSerializer(serializers.ModelSerializer):
    enrollees_count = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = (
            "code",
            "name",
            "enrollees_count",
        )

    def get_enrollees_count(self, obj) -> int:
        year_level = self.context["year_level"]
        semester = current_semester_get()

        enrollees = (
            models.Enrollment.objects.filter(
                semester=semester,
                student__course__school=obj,
                status=models.Enrollment.Statuses.ENROLLED,
            )
            .annotate(created_at__date=TruncDate("created_at__date"))
            .order_by("created_at__date")
            .values("created_at__date")
            .annotate(**{"total": Count("created_at__date")})
        )

        # TODO: Custom filterclass for year_level
        if year_level and year_level.isnumeric():
            enrollees = enrollees.filter(
                year_level=year_level,
            )

        return enrollees


class StudentRequestCreateSerializer(serializers.ModelSerializer):
    type = ChoiceField(choices_cls=models.StudentRequestTypes)

    class Meta:
        model = models.StudentRequest
        fields = ("type", "detail", "reason")


class ChangeScheduleRequestUpdateSerializer(serializers.ModelSerializer):
    remarks = serializers.CharField(max_length=500, write_only=True)

    class Meta:
        model = models.ChangeScheduleRequest
        fields = ("status", "remarks")


class AddSubjectRequestUpdateSerializer(serializers.ModelSerializer):
    remarks = serializers.CharField(max_length=500, write_only=True)

    class Meta:
        model = models.AddSubjectRequest
        fields = ("status", "remarks")


class StudentRequestOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.StudentRequest
        fields = ("request_no",)


class ChangeRequestRequestListSerializer(serializers.ModelSerializer):
    StudentSerializer = inline_serializer_class(
        model=models.Student,
        fields=("id_number", "year_level"),
        declared_fields={},
    )

    student = StudentSerializer()
    school = serializers.SerializerMethodField()

    class Meta:
        model = models.ChangeScheduleRequest
        fields = "__all__"

    def get_school(self, obj) -> str:
        try:
            return obj.student.course.school.name
        except:
            return None


class ChangeRequestRequestRetrieveSerializer(serializers.ModelSerializer):
    CourseSerializer = inline_serializer_class(
        model=Course,
        fields=("code", "sub_code", "name", "major"),
        declared_fields={},
    )

    StudentSerializer = inline_serializer_class(
        model=models.Student,
        fields=("first_name", "last_name", "id_number", "year_level", "course"),
        declared_fields={"course": CourseSerializer()},
    )

    UserSerializer = inline_serializer_class(
        model=User,
        fields=("username", "first_name", "last_name"),
        declared_fields={},
    )

    ReviewHistorySerializer = inline_serializer_class(
        model=models.StudentRequestReviewHistory,
        fields=("user", "remarks", "status", "created_at"),
        declared_fields={"user": UserSerializer()},
    )

    student = StudentSerializer()
    school = serializers.SerializerMethodField()
    review_histories = ReviewHistorySerializer(many=True)

    class Meta:
        model = models.ChangeScheduleRequest
        fields = "__all__"

    def get_school(self, obj) -> str:
        try:
            return obj.student.course.school.name
        except:
            return None


class AddSubjectRequestListSerializer(serializers.ModelSerializer):
    StudentSerializer = inline_serializer_class(
        model=models.Student,
        fields=("id_number", "year_level"),
        declared_fields={},
    )

    student = StudentSerializer()
    school = serializers.SerializerMethodField()

    class Meta:
        model = models.AddSubjectRequest
        fields = "__all__"

    def get_school(self, obj) -> str:
        try:
            return obj.student.course.school.name
        except:
            return None


class AddSubjectRequestRetrieveSerializer(serializers.ModelSerializer):
    CourseSerializer = inline_serializer_class(
        model=Course,
        fields=("code", "sub_code", "name", "major"),
        declared_fields={},
    )

    StudentSerializer = inline_serializer_class(
        model=models.Student,
        fields=("first_name", "last_name", "id_number", "year_level", "course"),
        declared_fields={"course": CourseSerializer()},
    )

    UserSerializer = inline_serializer_class(
        model=User,
        fields=("username", "first_name", "last_name"),
        declared_fields={},
    )

    ReviewHistorySerializer = inline_serializer_class(
        model=models.StudentRequestReviewHistory,
        fields=("user", "remarks", "status", "created_at"),
        declared_fields={"user": UserSerializer()},
    )

    student = StudentSerializer()
    school = serializers.SerializerMethodField()
    review_histories = ReviewHistorySerializer(many=True)

    class Meta:
        model = models.AddSubjectRequest
        fields = "__all__"

    def get_school(self, obj) -> str:
        try:
            return obj.student.course.school.name
        except:
            return None


class OpenClassRequestListSerializer(serializers.ModelSerializer):
    StudentSerializer = inline_serializer_class(
        model=models.Student,
        fields=("id_number", "year_level"),
        declared_fields={},
    )

    student = StudentSerializer()
    school = serializers.SerializerMethodField()

    class Meta:
        model = models.OpenClassRequest
        fields = "__all__"

    def get_school(self, obj) -> str:
        try:
            return obj.student.course.school.name
        except:
            return None


class OpenClassRequestRetrieveSerializer(serializers.ModelSerializer):
    CourseSerializer = inline_serializer_class(
        model=Course,
        fields=("code", "sub_code", "name", "major"),
        declared_fields={},
    )

    StudentSerializer = inline_serializer_class(
        model=models.Student,
        fields=("first_name", "last_name", "id_number", "year_level", "course"),
        declared_fields={"course": CourseSerializer()},
    )

    UserSerializer = inline_serializer_class(
        model=User,
        fields=("username", "first_name", "last_name"),
        declared_fields={},
    )

    ReviewHistorySerializer = inline_serializer_class(
        model=models.StudentRequestReviewHistory,
        fields=("user", "remarks", "status", "created_at"),
        declared_fields={"user": UserSerializer()},
    )

    student = StudentSerializer()
    school = serializers.SerializerMethodField()
    review_histories = serializers.SerializerMethodField()

    class Meta:
        model = models.OpenClassRequest
        fields = "__all__"

    def get_school(self, obj) -> str:
        try:
            return obj.student.course.school.name
        except:
            return None

    def get_review_histories(self, obj) -> ReviewHistorySerializer(many=True):
        review_history = obj.review_histories.all().order_by("-created_at")
        return self.ReviewHistorySerializer(review_history, many=True).data


class OpenClassRequestUpdateSerializer(serializers.ModelSerializer):
    remarks = serializers.CharField(max_length=500, write_only=True)
    notify_student = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = models.OpenClassRequest
        fields = ("status", "remarks", "notify_student")


class WithdrawalRequestListSerializer(serializers.ModelSerializer):
    StudentSerializer = inline_serializer_class(
        model=models.Student,
        fields=("id_number", "year_level"),
        declared_fields={},
    )

    student = StudentSerializer()
    school = serializers.SerializerMethodField()

    class Meta:
        model = models.WithdrawalRequest
        fields = "__all__"

    def get_school(self, obj) -> str:
        try:
            return obj.student.course.school.name
        except:
            return None


class WithdrawalRequestRetrieveSerializer(serializers.ModelSerializer):
    CourseSerializer = inline_serializer_class(
        model=Course,
        fields=("code", "sub_code", "name", "major"),
        declared_fields={},
    )

    StudentSerializer = inline_serializer_class(
        model=models.Student,
        fields=("first_name", "last_name", "id_number", "year_level", "course"),
        declared_fields={"course": CourseSerializer()},
    )

    UserSerializer = inline_serializer_class(
        model=User,
        fields=("username", "first_name", "last_name"),
        declared_fields={},
    )

    ReviewHistorySerializer = inline_serializer_class(
        model=models.StudentRequestReviewHistory,
        fields=("user", "remarks", "status", "created_at"),
        declared_fields={"user": UserSerializer()},
    )

    student = StudentSerializer()
    school = serializers.SerializerMethodField()
    review_histories = serializers.SerializerMethodField()

    class Meta:
        model = models.WithdrawalRequest
        fields = "__all__"

    def get_school(self, obj) -> str:
        try:
            return obj.student.course.school.name
        except:
            return None

    def get_review_histories(self, obj) -> ReviewHistorySerializer(many=True):
        review_history = obj.review_histories.all().order_by("-created_at")
        return self.ReviewHistorySerializer(review_history, many=True).data


class WithdrawalRequestUpdateSerializer(serializers.ModelSerializer):
    remarks = serializers.CharField(max_length=500, write_only=True)
    notify_student = serializers.BooleanField(required=False, default=False)
    type = serializers.ChoiceField(
        choices=models.WithdrawalRequest.Types, required=False
    )

    class Meta:
        model = models.OpenClassRequest
        fields = ("status", "remarks", "type", "notify_student")


class StudentEnrollmentSubjectListSerializer(serializers.ModelSerializer):
    BuildingSerializer = inline_serializer_class(
        model=Building,
        fields=("name",),
        declared_fields={},
    )

    RoomSerializer = inline_serializer_class(
        model=Room,
        fields=("number", "name", "floor_no", "wing", "building"),
        declared_fields={"building": BuildingSerializer()},
    )

    ClassScheduleSerializer = inline_serializer_class(
        model=ClassSchedule,
        fields=("room", "time_in", "time_out", "day"),
        declared_fields={"room": RoomSerializer()},
    )
    ClassSerializer = inline_serializer_class(
        model=Class,
        fields=("id", "class_code", "has_available_slot", "class_schedules"),
        declared_fields={
            "class_schedules": ClassScheduleSerializer(many=True),
            "has_available_slot": serializers.BooleanField(
                source="has_available_slot_for_reservation"
            ),
        },
    )

    SubjectSerializer = inline_serializer_class(
        model=Subject,
        fields=(
            "course_code",
            "course_number",
            "descriptive_code",
            "descriptive_title",
            "units",
        ),
        declared_fields={},
    )

    subject = SubjectSerializer()
    has_pending_prereq = serializers.SerializerMethodField()
    classes = serializers.SerializerMethodField()
    semester = serializers.CharField(source="curriculum_period.semester")
    year_level = serializers.CharField(source="curriculum_period.year_level")

    class Meta:
        model = CurriculumSubject
        fields = (
            "id",
            "has_pending_prereq",
            "semester",
            "year_level",
            "subject",
            "classes",
        )

    def get_has_pending_prereq(self, obj):
        return obj.has_pending_prerequisite(self.context.get("passed_curr_subj_ids"))

    def get_classes(self, obj) -> ClassSerializer(many=True):
        semester = next_semester_get()
        classes = Class.objects.filter(subject=obj.subject, semester=semester)

        return self.ClassSerializer(classes, many=True).data
