from random import choice

import pytest
from django.urls import reverse
from rest_framework import status

from university.core.students.models import (
    AddSubjectRequest,
    ChangeScheduleRequest,
    Enrollment,
    OpenClassRequest,
    Student,
    StudentRequestTypes,
    WithdrawalRequest,
)
from university.framework.tests import apply_perms, assert_paginated_response, fake


@pytest.mark.django_db
class TestStudentProfileApi:
    def test_retrieve(self, student_api_client):
        url = reverse("university.core.students:student:profile")
        response = student_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_update(self, student_api_client):
        url = reverse("university.core.students:student:profile")
        data = {
            "gender": choice(Student.Genders.values),
            "civil_status": choice(Student.CivilStatuses.values),
            "birth_date": fake.date(),
            "birth_place": fake.address(),
            "religion": None,
            "citizenship": choice(Student.Citizenships.values),
            "nationality": choice(Student.Nationalities.values),
            "email": fake.email(),
            "phone_no": fake.mobile_number(),
            "province": fake.province(),
            "city": fake.city(),
            "barangay": fake.province_lgu(),
            "street": fake.street_address(),
            "zip_code": fake.postcode(),
            "home_phone_no": fake.mobile_number(),
            "local_address": fake.address(),
            "local_phone_no": fake.mobile_number(),
            "father_name": fake.name_male(),
            "father_occupation": fake.job(),
            "mother_name": fake.name_female(),
            "mother_occupation": fake.job(),
            "guardian_name": fake.name(),
            "guardian_address": fake.address(),
            "emergency_contact_name": fake.name(),
            "emergency_contact_email": fake.email(),
            "emergency_contact_phone_no": fake.mobile_number(),
        }
        response = student_api_client.put(url, data)
        assert response.status_code == status.HTTP_200_OK

        url = reverse("university.core.students:student:profile")
        get_response = student_api_client.get(url)
        profile = get_response.json()

        for field, value in data.items():
            assert profile.get(field) == value

    def test_partial_update(self, student_api_client):
        url = reverse("university.core.students:student:profile")
        data = {
            "province": fake.province(),
            "city": fake.city(),
            "barangay": fake.province_lgu(),
            "street": fake.street_address(),
            "zip_code": fake.postcode(),
        }
        response = student_api_client.put(url, data)
        assert response.status_code == status.HTTP_200_OK

        url = reverse("university.core.students:student:profile")
        get_response = student_api_client.get(url)
        profile = get_response.json()

        for field, value in data.items():
            assert profile.get(field) == value


@pytest.mark.django_db
class TestStudentListRetrieveAPIView:
    def test_students_list(self, staff_api_client, student_factory):
        students = [student_factory() for _ in range(5)]
        url = reverse("university.core.students:students-list")
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert_paginated_response(response.data)
        assert len(response.data["results"]) == len(students)

    def test_students_retrieve(self, staff_api_client, student):
        url = reverse(
            "university.core.students:students-detail", kwargs={"pk": student.pk}
        )
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestStudentEnrollmentLatestAPIView:
    url = reverse("university.core.students:student:enrollments-latest")

    def test_student_enrollment_retrieve(self, student_api_client, enrollment):
        response = student_api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK

    def test_student_enrollment_retrieve_404(self, student_api_client):
        response = student_api_client.get(self.url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_student_pre_loaded_enrollment_step_1(self, student_api_client, enrollment):
        """Step 1 should be enabled for Enrollment during pre-loaded enrollment"""
        # Pre-loaded enrollment should start from step 1
        enrollment.step = Enrollment.Steps.START
        enrollment.save()

        data = {
            "current_address": fake.address(),
            "contact_number": fake.mobile_number(),
            "personal_email": fake.email(),
            "institutional_email": fake.email(),
            "father_name": fake.name_male(),
            "father_occupation": fake.job(),
            "mother_name": fake.name_female(),
            "mother_occupation": fake.job(),
            "is_living_with_parents": fake.pybool(),
            "emergency_contact_name": fake.name(),
            "emergency_contact_address": fake.address(),
            "emergency_contact_phone_no": fake.mobile_number(),
            "emergency_contact_email": fake.email(),
            "step": Enrollment.Steps.INFORMATION,
        }
        response = student_api_client.patch(self.url, data)
        assert response.status_code == status.HTTP_200_OK

        enrollment.refresh_from_db()
        exclude = ("step",)

        for field, value in data.items():
            if field in exclude:
                continue
            assert getattr(enrollment, field) == value

        assert enrollment.step == Enrollment.Steps.INFORMATION

    def test_student_enrollment_step_2(self, student_api_client, enrollment, personnel):
        """Step 2 updates during Enrollment should not be allowed"""
        enrollment.step = Enrollment.Steps.INFORMATION
        enrollment.save()

        data = {
            "is_employee": True,
            "employee_no": personnel.user.username,
            "is_employee_dependent": False,
            "dependent_employee_no": "",
            "dependent_relationship": "F",
            "is_working_scholar": True,
            "has_enrolled_sibling": False,
            "sibling_student_numbers": [],
            "step": Enrollment.Steps.DISCOUNTS,
        }

        response = student_api_client.patch(self.url, data)
        assert response.status_code == status.HTTP_200_OK

    def test_student_enrollment_step_3(
        self, student_api_client, enrollment, curriculum_subject, klass
    ):
        """Step 3 updates during Enrollment should not be allowed"""
        enrollment.step = Enrollment.Steps.DISCOUNTS
        enrollment.save()

        data = {
            "step": Enrollment.Steps.SUBJECTS,
            "enrolled_classes": [
                {
                    "klass": klass.id,
                    "curriculum_subject": curriculum_subject.id,
                }
            ],
        }

        response = student_api_client.patch(self.url, data)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestStudentCurriculumRetrieveAPIView:
    url = reverse("university.core.students:student:curriculum-detail")

    def test_student_curriculum_retrieve(self, student_api_client, student):
        response = student_api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestStudentEnrollmentGradeListAPIView:
    url = reverse("university.core.students:student:grades-list")

    def test_student_grades_list(self, student_api_client, student):
        response = student_api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestEnrolleePerSchoolListAPIView:
    url = reverse("university.core.students:enrollees-per-school")

    def test_enrollees_per_school(self, staff_api_client):
        response = staff_api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestFailedStudentPerSchoolListAPIView:
    url = reverse("university.core.students:failed-students-per-school")

    def test_failed_students_per_school(self, staff_api_client):
        response = staff_api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestInterviewedFailedStudentPerSchoolListAPIView:
    url = reverse("university.core.students:interviewed-failed-students-per-school")

    def test_interviewed_failed_students_per_school(self, staff_api_client):
        response = staff_api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestInterviewedFailedStudentPerSchoolListAPIView:
    url = reverse("university.core.students:enrollees-scholars-per-school")

    def test_enrollees_scholars_per_school(self, staff_api_client):
        response = staff_api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestStudentRequestViewSet:
    def test_student_request_create(self, student_api_client):
        data = {
            "type": StudentRequestTypes.CHANGE_SCHEDULE.value,
            "detail": str(fake.words()),
            "reason": str(fake.words()),
        }
        url = reverse("university.core.students:student:student-request-create")
        response = student_api_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestStudentChangeScheduleRequestListRetrieveUpdate:
    @apply_perms("core_students.view_changeschedulerequest", client="staff_api_client")
    def test_change_schedule_request_list(
        self, staff_api_client, change_schedule_request_factory
    ):
        rooms = [change_schedule_request_factory() for _ in range(5)]
        url = reverse("university.core.students:change-schedule-requests-list")
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert_paginated_response(response.data)
        assert len(response.data["results"]) == len(rooms)

    @apply_perms("core_students.view_changeschedulerequest", client="staff_api_client")
    def test_change_schedule_request_retrieve(
        self, staff_api_client, change_schedule_request
    ):
        url = reverse(
            "university.core.students:change-schedule-requests-detail",
            kwargs={"pk": change_schedule_request.pk},
        )
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    @apply_perms(
        "core_students.change_changeschedulerequest", client="staff_api_client"
    )
    def test_change_schedule_request_update(
        self, staff_api_client, change_schedule_request
    ):
        data = {
            "status": ChangeScheduleRequest.Statuses.INREVIEW,
            "remarks": fake.sentence(),
        }
        url = reverse(
            "university.core.students:change-schedule-requests-detail",
            kwargs={"pk": change_schedule_request.pk},
        )
        response = staff_api_client.patch(url, data)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestStudentAddSubjectListRetrieveUpdate:
    @apply_perms("core_students.view_addsubjectrequest", client="staff_api_client")
    def test_add_subject_request_retrieve(self, staff_api_client, add_subject_request):
        url = reverse(
            "university.core.students:add-subject-requests-detail",
            kwargs={"pk": add_subject_request.pk},
        )
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    @apply_perms("core_students.view_addsubjectrequest", client="staff_api_client")
    def test_add_subject_request_retrieve(self, staff_api_client, add_subject_request):
        url = reverse(
            "university.core.students:add-subject-requests-detail",
            kwargs={"pk": add_subject_request.pk},
        )
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    @apply_perms("core_students.change_addsubjectrequest", client="staff_api_client")
    def test_open_class_request_update(self, staff_api_client, add_subject_request):
        data = {
            "status": AddSubjectRequest.Statuses.INREVIEW,
            "remarks": fake.sentence(),
        }
        url = reverse(
            "university.core.students:add-subject-requests-detail",
            kwargs={"pk": add_subject_request.pk},
        )
        response = staff_api_client.patch(url, data)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestStudentOpenClassRequestListRetrieveUpdate:
    @apply_perms("core_students.view_openclassrequest", client="staff_api_client")
    def test_open_class_request_list(
        self, staff_api_client, open_class_request_factory
    ):
        rooms = [open_class_request_factory() for _ in range(5)]
        url = reverse("university.core.students:open-class-requests-list")
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert_paginated_response(response.data)
        assert len(response.data["results"]) == len(rooms)

    @apply_perms("core_students.view_openclassrequest", client="staff_api_client")
    def test_open_class_request_retrieve(self, staff_api_client, open_class_request):
        url = reverse(
            "university.core.students:open-class-requests-detail",
            kwargs={"pk": open_class_request.pk},
        )
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    @apply_perms("core_students.change_openclassrequest", client="staff_api_client")
    def test_open_class_request_update(self, staff_api_client, open_class_request):
        data = {
            "status": OpenClassRequest.Statuses.FOR_ENCODING,
            "remarks": fake.sentence(),
            "notify_student": True,
        }
        url = reverse(
            "university.core.students:open-class-requests-detail",
            kwargs={"pk": open_class_request.pk},
        )
        response = staff_api_client.patch(url, data)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestStudentWithdrawalRequestListRetrieveUpdate:
    @apply_perms("core_students.view_withdrawalrequest", client="staff_api_client")
    def test_withdrawal_request_list(
        self, staff_api_client, withdrawal_request_factory
    ):
        rooms = [withdrawal_request_factory() for _ in range(5)]
        url = reverse("university.core.students:withdrawal-requests-list")
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert_paginated_response(response.data)
        assert len(response.data["results"]) == len(rooms)

    @apply_perms("core_students.view_withdrawalrequest", client="staff_api_client")
    def test_withdrawal_request_retrieve(self, staff_api_client, withdrawal_request):
        url = reverse(
            "university.core.students:withdrawal-requests-detail",
            kwargs={"pk": withdrawal_request.pk},
        )
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    @apply_perms("core_students.change_withdrawalrequest", client="staff_api_client")
    def test_withdrawal_request_update(self, staff_api_client, withdrawal_request):
        data = {
            "status": WithdrawalRequest.Statuses.FOR_ENCODING,
            "remarks": fake.sentence(),
            "notify_student": True,
        }
        url = reverse(
            "university.core.students:withdrawal-requests-detail",
            kwargs={"pk": withdrawal_request.pk},
        )
        response = staff_api_client.patch(url, data)
        assert response.status_code == status.HTTP_200_OK
