from decimal import Decimal

from rest_framework import serializers
from rest_polymorphic.serializers import PolymorphicSerializer

from university.core.accounts.models import AcademicYear, Semester
from university.core.accounts.selectors import current_semester_get
from university.core.accounts.serializers import (
    AcademicYearBaseSerializer,
    SchoolSerializer,
    UserDetailBaseSerializer,
)
from university.core.students.models import Enrollment
from university.framework.serializers import inline_serializer_class

from . import models


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Subject
        fields = "__all__"


class SubjectCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Subject
        fields = "__all__"


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Course
        fields = "__all__"


class CourseBaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Course
        fields = ("id", "code", "sub_code", "name")


class SubjectSubSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Subject
        fields = (
            "id",
            "ref_id",
            "course_code",
            "course_number",
            "descriptive_code",
            "descriptive_title",
            "units",
            "no_of_hours",
        )


class ClassRetrieveSerializer(serializers.ModelSerializer):
    course = CourseBaseSerializer()
    school = SchoolSerializer()

    class Meta:
        model = models.Class
        fields = "__all__"


class ClassCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Class
        fields = "__all__"


class CurriculumCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Curriculum
        fields = "__all__"


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Room
        fields = "__all__"


class ClassScheduleSerializer(serializers.ModelSerializer):
    room = RoomSerializer()

    class Meta:
        model = models.ClassSchedule
        fields = ("room", "time_in", "time_out", "day")


class CurriculumSubjectSerializer(serializers.ModelSerializer):
    subject = SubjectSubSerializer()

    class Meta:
        model = models.CurriculumSubject
        fields = "__all__"


class ClassSerializer(serializers.ModelSerializer):
    AcademicYearSerializer = inline_serializer_class(
        model=AcademicYear,
        fields=("id", "year_start", "year_end"),
    )

    SemesterSerializer = inline_serializer_class(
        model=Semester,
        fields=("academic_year", "term"),
        declared_fields={"academic_year": AcademicYearSerializer()},
    )

    subject = SubjectSubSerializer()
    class_schedules = ClassScheduleSerializer(many=True)
    units = serializers.SerializerMethodField()
    semester = SemesterSerializer()

    class Meta:
        model = models.Class
        fields = "__all__"

    def get_units(self, obj) -> Decimal:
        return obj.subject.units if obj.subject else 0


class CurriculumSubjectRequisiteSerializer(serializers.ModelSerializer):
    requisite_subject = serializers.SerializerMethodField()

    class Meta:
        model = models.CurriculumSubjectRequisite
        fields = "__all__"

    def get_requisite_subject(self, obj):
        return SubjectSubSerializer(obj.requisite_subject.subject).data


class CurriculumSubjectListRetrieveSerializer(serializers.ModelSerializer):
    subject = SubjectSubSerializer()
    requisites = CurriculumSubjectRequisiteSerializer(many=True)

    class Meta:
        model = models.CurriculumSubject
        fields = "__all__"


class CurriculumPeriodSerializer(serializers.ModelSerializer):
    curriculum_subjects = CurriculumSubjectListRetrieveSerializer(many=True)
    total_units = serializers.DecimalField(
        source="get_total_units", max_digits=9, decimal_places=2
    )

    class Meta:
        model = models.CurriculumPeriod
        fields = "__all__"


class CurriculumRetrieveSerializer(serializers.ModelSerializer):
    course = CourseBaseSerializer()
    curriculum_periods = CurriculumPeriodSerializer(many=True)

    class Meta:
        model = models.Curriculum
        fields = "__all__"


class CurriculumSerializer(serializers.ModelSerializer):
    course = CourseBaseSerializer()

    class Meta:
        model = models.Curriculum
        fields = "__all__"


class CurriculumPeriodListRetrieveSerializer(serializers.ModelSerializer):
    curriculum = CurriculumSerializer()
    curriculum_subjects = CurriculumSubjectListRetrieveSerializer(many=True)
    total_units = serializers.DecimalField(
        source="get_total_units", max_digits=9, decimal_places=2
    )

    class Meta:
        model = models.CurriculumPeriod
        fields = "__all__"


class ClassListSerializer(serializers.ModelSerializer):
    curriculum_subject = CurriculumSubjectListRetrieveSerializer()
    total_students_enrolled = serializers.DecimalField(
        source="get_total_students_enrolled", max_digits=9, decimal_places=2
    )
    instructor = serializers.SerializerMethodField()

    class Meta:
        model = models.Class
        fields = "__all__"

    def get_instructor(self, obj) -> UserDetailBaseSerializer:
        if obj.instructor:
            return UserDetailBaseSerializer(obj.instructor.user).data
        return None


class ClassStudentListSerializer(serializers.ModelSerializer):
    enrolled_students = serializers.SerializerMethodField()
    instructor = serializers.SerializerMethodField()

    class Meta:
        model = models.Class
        fields = "__all__"

    def get_enrolled_students(self, obj):
        from university.core.students.models import EnrollmentSubjectSchedule
        from university.core.students.serializers import (
            EnrollmentSubjectScheduleRetrieveSubSerializer,
        )

        enrolled = obj.enrolled_students.filter(
            status=EnrollmentSubjectSchedule.Statuses.APPROVED
        )
        return EnrollmentSubjectScheduleRetrieveSubSerializer(enrolled, many=True).data

    def get_instructor(self, obj) -> UserDetailBaseSerializer:
        if obj.instructor:
            return UserDetailBaseSerializer(obj.instructor.user).data
        return None


class CurriculumPeriodBaseSerializer(serializers.ModelSerializer):
    total_units = serializers.DecimalField(
        source="get_total_units", max_digits=9, decimal_places=2
    )

    class Meta:
        model = models.CurriculumPeriod
        fields = ("year_level", "semester", "total_units")


class BuildingSerializer(serializers.ModelSerializer):
    schools = SchoolSerializer(many=True)

    class Meta:
        model = models.Building
        fields = "__all__"


class FeeSerializer(serializers.ModelSerializer):
    academic_year = AcademicYearBaseSerializer()

    class Meta:
        model = models.Fee
        fields = "__all__"


class FeeSpecificationSerializer(serializers.ModelSerializer):
    fees = FeeSerializer(many=True)
    academic_year = AcademicYearBaseSerializer()

    class Meta:
        model = models.FeeSpecification
        fields = "__all__"


class OtherFeeSpecificationSerializer(serializers.ModelSerializer):
    fees = FeeSerializer(many=True)
    school = SchoolSerializer()
    subject = SubjectSubSerializer()
    academic_year = AcademicYearBaseSerializer()

    class Meta:
        model = models.OtherFeeSpecification
        fields = "__all__"


class MiscellaneousFeeSpecificationSerializer(serializers.ModelSerializer):
    fees = FeeSerializer(many=True)
    school = SchoolSerializer()
    subject = SubjectSubSerializer()
    academic_year = AcademicYearBaseSerializer()

    class Meta:
        model = models.MiscellaneousFeeSpecification
        fields = "__all__"


class FeeSpecificationPolymorphicSerializer(PolymorphicSerializer):
    model_serializer_mapping = {
        models.FeeSpecification: FeeSpecificationSerializer,
        models.OtherFeeSpecification: OtherFeeSpecificationSerializer,
        models.MiscellaneousFeeSpecification: MiscellaneousFeeSpecificationSerializer,
    }


class ClassificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Classification
        fields = "__all__"


class PersonnelClassScheduleSerializer(serializers.ModelSerializer):
    SubjectSerializer = inline_serializer_class(
        model=models.Subject,
        fields=(
            "charge_code",
            "course_code",
            "course_number",
            "descriptive_code",
            "descriptive_title",
            "units",
        ),
        declared_fields={},
    )
    CourseSSerializer = inline_serializer_class(
        model=models.Course,
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
        model=models.Class,
        fields=("id", "class_code", "no_of_enrolled", "subject", "course"),
        declared_fields={
            "no_of_enrolled": serializers.IntegerField(
                source="get_total_students_enrolled"
            ),
            "subject": SubjectSerializer(),
            "course": CourseSerializer(),
        },
    )

    RoomSerializer = inline_serializer_class(
        model=models.Room,
        fields=("name", "number", "floor_no"),
        declared_fields={},
    )

    room = RoomSerializer()
    klass = ClassSerializer()

    class Meta:
        model = models.ClassSchedule
        fields = "__all__"


class OpenClassPerSchoolSerializer(serializers.ModelSerializer):
    no_of_open_classes = serializers.SerializerMethodField()

    class Meta:
        model = models.School
        fields = ("code", "name", "no_of_open_classes")

    def get_no_of_open_classes(self, obj) -> int:
        year_level = self.context["year_level"]
        semester = current_semester_get()

        classes = models.Class.objects.filter(
            semester=semester, course__school=obj, is_dissolved=False
        )

        # TODO: Custom filterclass for year_level
        if year_level and year_level.isnumeric():
            classes = classes.filter(year_level=year_level)

        return classes.count()


class OpenClassEnrolleePerCourseSerializer(serializers.ModelSerializer):
    no_of_open_classes = serializers.SerializerMethodField()
    no_of_enrollees = serializers.SerializerMethodField()

    class Meta:
        model = models.Course
        fields = ("code", "name", "major", "no_of_open_classes", "no_of_enrollees")

    def get_no_of_open_classes(self, obj) -> int:
        year_level = self.context["year_level"]
        school = self.context["school"]
        semester = current_semester_get()

        classes = models.Class.objects.filter(
            semester=semester, course=obj, is_dissolved=False
        )

        # TODO: Custom filterclass for year_level
        if year_level and year_level.isnumeric():
            classes = classes.filter(year_level=year_level)

        if school:
            classes = classes.filter(course__school=school)

        return classes.count()

    def get_no_of_enrollees(self, obj) -> int:
        from university.core.students.models import Enrollment

        year_level = self.context["year_level"]
        school = self.context["school"]
        semester = current_semester_get()

        enrollments = Enrollment.objects.filter(semester=semester, student__course=obj)

        # TODO: Custom filterclass for year_level
        if year_level and year_level.isnumeric():
            enrollments = enrollments.filter(year_level=year_level)

        if school:
            enrollments = enrollments.filter(sstudent__course__school=school)

        return enrollments.count()


class AnnouncementsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Announcement
        fields = ("id", "start_date", "end_date", "subject", "content")


class ClassGradeStatePerSchoolSerializer(serializers.ModelSerializer):
    prelim_draft = serializers.SerializerMethodField()
    prelim_submitted = serializers.SerializerMethodField()
    midterm_draft = serializers.SerializerMethodField()
    midterm_submitted = serializers.SerializerMethodField()
    final_draft = serializers.SerializerMethodField()
    final_submitted = serializers.SerializerMethodField()
    total_classes = serializers.SerializerMethodField()

    class Meta:
        model = models.School
        fields = (
            "code",
            "name",
            "total_classes",
            "prelim_draft",
            "prelim_submitted",
            "midterm_draft",
            "midterm_submitted",
            "final_draft",
            "final_submitted",
        )

    def get_classes(self, obj):
        year_level = self.context["year_level"]
        semester = current_semester_get()

        classes = models.Class.objects.filter(
            semester=semester, course__school=obj, is_dissolved=False
        )

        # TODO: Custom filterclass for year_level
        if year_level and year_level.isnumeric():
            classes = classes.filter(year_level=year_level)

        return classes

    def get_total_classes(self, obj) -> int:
        return self.get_classes(obj).count()

    def get_prelim_draft(self, obj) -> int:
        classes = self.get_classes(obj)
        return classes.filter(
            grade_states__prelim_grade_state=models.ClassGradeState.States.DRAFT
        ).count()

    def get_prelim_submitted(self, obj) -> int:
        classes = self.get_classes(obj)
        return classes.filter(
            grade_states__prelim_grade_state=models.ClassGradeState.States.SUBMITTED
        ).count()

    def get_midterm_draft(self, obj) -> int:
        classes = self.get_classes(obj)
        return classes.filter(
            grade_states__midterm_grade_state=models.ClassGradeState.States.DRAFT
        ).count()

    def get_midterm_submitted(self, obj) -> int:
        classes = self.get_classes(obj)
        return classes.filter(
            grade_states__midterm_grade_state=models.ClassGradeState.States.SUBMITTED
        ).count()

    def get_final_draft(self, obj) -> int:
        classes = self.get_classes(obj)
        return classes.filter(
            grade_states__final_grade_state=models.ClassGradeState.States.DRAFT
        ).count()

    def get_final_submitted(self, obj) -> int:
        classes = self.get_classes(obj)
        return classes.filter(
            grade_states__final_grade_state=models.ClassGradeState.States.SUBMITTED
        ).count()
