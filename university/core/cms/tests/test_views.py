from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status

from university.core.cms import models
from university.framework.tests import apply_perms, assert_paginated_response, fake


@pytest.mark.django_db
class TestRoomViewSet:
    @apply_perms("core_cms.view_room", client="staff_api_client")
    def test_rooms_list(self, staff_api_client, room_factory):
        rooms = [room_factory() for _ in range(5)]
        url = reverse("university.core.cms:rooms-list")
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert_paginated_response(response.data)
        assert len(response.data["results"]) == len(rooms)

    @apply_perms("core_cms.add_room", client="staff_api_client")
    def test_rooms_create(self, staff_api_client, school, building, classification):
        data = {
            "school": school.id,
            "building": building.id,
            "classification": classification.id,
            "number": fake.floor_unit_number(),
            "name": fake.building_number(),
            "size": "8x8",
            "floor_no": int(fake.floor_number()),
            "wing": "East",
            "capacity": fake.pyint(20, 40),
            "furniture": str(fake.pyint(20, 40)),
        }
        url = reverse("university.core.cms:rooms-list")
        response = staff_api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED

        assert_fields = [
            "number",
            "name",
            "size",
            "floor_no",
            "wing",
            "capacity",
            "furniture",
        ]

        for field in assert_fields:
            assert response.data[field] == data[field]

        room = models.Room.objects.get(pk=response.data.get("id"))
        assert room.school == school
        assert room.building == building
        assert room.classification == classification

    @apply_perms("core_cms.view_room", client="staff_api_client")
    def test_rooms_retrieve(self, staff_api_client, room):
        url = reverse("university.core.cms:rooms-detail", kwargs={"pk": room.pk})
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert_fields = [
            "id",
            "number",
            "name",
            "size",
            "floor_no",
            "wing",
            "capacity",
            "furniture",
        ]

        for field in assert_fields:
            assert response.data.get(field) == getattr(room, field)

        assert response.data["school"] == room.school.id
        assert response.data["building"] == room.building.id
        assert response.data["classification"] == room.classification.id

    @apply_perms("core_cms.change_room", client="staff_api_client")
    def test_rooms_update(
        self, staff_api_client, room, school, building, classification
    ):
        data = {
            "school": school.id,
            "building": building.id,
            "classification": classification.id,
            "number": fake.floor_unit_number(),
            "name": fake.building_number(),
            "size": "8x8",
            "floor_no": int(fake.floor_number()),
            "wing": "East",
            "capacity": fake.pyint(20, 40),
            "furniture": str(fake.pyint(20, 40)),
        }
        url = reverse("university.core.cms:rooms-detail", kwargs={"pk": room.pk})
        response = staff_api_client.put(url, data)
        assert response.status_code == status.HTTP_200_OK

        room.refresh_from_db()
        assert_fields = [
            "number",
            "name",
            "size",
            "floor_no",
            "wing",
            "capacity",
            "furniture",
        ]

        for field in assert_fields:
            assert response.data[field] == getattr(room, field)

        assert room.school == school
        assert room.building == building
        assert room.classification == classification

    @apply_perms("core_cms.change_room", client="staff_api_client")
    def test_rooms_partial_update(
        self, staff_api_client, room, school, building, classification
    ):
        data = {
            "school": school.id,
            "building": building.id,
            "classification": classification.id,
            "number": fake.floor_unit_number(),
        }
        url = reverse("university.core.cms:rooms-detail", kwargs={"pk": room.pk})
        response = staff_api_client.patch(url, data)
        assert response.status_code == status.HTTP_200_OK

        room.refresh_from_db()
        assert room.school == school
        assert room.building == building
        assert room.classification == classification
        assert room.number == data["number"]

    @apply_perms("core_cms.delete_room", client="staff_api_client")
    def test_rooms_destroy(self, staff_api_client, room):
        url = reverse("university.core.cms:rooms-detail", kwargs={"pk": room.pk})
        response = staff_api_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not models.Room.active_objects.filter(pk=room.id).exists()


@pytest.mark.django_db
class TestCourseListRetrieveAPIView:
    @apply_perms("core_cms.view_course", client="staff_api_client")
    def test_course_list(self, staff_api_client, course_factory):
        courses = [course_factory() for _ in range(5)]
        url = reverse("university.core.cms:courses-list")
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert_paginated_response(response.data)
        assert len(response.data["results"]) == len(courses)

    @apply_perms("core_cms.view_course", client="staff_api_client")
    def test_course_retrieve(self, staff_api_client, course):
        url = reverse("university.core.cms:courses-detail", kwargs={"pk": course.pk})
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert_fields = [
            "id",
            "level",
            "category",
            "code",
            "sub_code",
            "name",
            "major",
            "minor",
            "degree_class",
            "duration",
            "duration_unit",
            "is_accredited",
            "accredited_year",
            "accredited_year",
            "accredited_year",
        ]

        for field in assert_fields:
            assert response.data.get(field) == getattr(course, field)

        assert response.data["school"] == course.school.id


@pytest.mark.django_db
class TestBuildingListRetrieveAPIView:
    @apply_perms("core_cms.view_building", client="staff_api_client")
    def test_building_list(self, staff_api_client, building_factory):
        building = [building_factory() for _ in range(5)]
        url = reverse("university.core.cms:buildings-list")
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert_paginated_response(response.data)
        assert len(response.data["results"]) == len(building)

    @apply_perms("core_cms.view_building", client="staff_api_client")
    def test_building_retrieve(self, staff_api_client, building):
        url = reverse(
            "university.core.cms:buildings-detail", kwargs={"pk": building.pk}
        )
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert_fields = [
            "id",
            "ref_id",
            "sub_code",
            "no_of_floors",
            "name",
            "campus",
            "notes",
            "is_active",
        ]

        for field in assert_fields:
            assert response.data.get(field) == getattr(building, field)

        assert len(response.data["schools"]) == building.schools.count()


@pytest.mark.django_db
class TestFeeListRetrieveAPIView:
    @apply_perms("core_cms.view_fee", client="staff_api_client")
    def test_fee_list(self, staff_api_client, fee_factory):
        fee = [fee_factory() for _ in range(5)]
        url = reverse("university.core.cms:fees-list")
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert_paginated_response(response.data)
        assert len(response.data["results"]) == len(fee)

    @apply_perms("core_cms.view_fee", client="staff_api_client")
    def test_fee_retrieve(self, staff_api_client, fee):
        url = reverse("university.core.cms:fees-detail", kwargs={"pk": fee.pk})
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert_fields = [
            "id",
            "code",
            "name",
            "type",
            "description",
            "remarks",
        ]

        for field in assert_fields:
            assert response.data.get(field) == getattr(fee, field)

        assert response.data["amount"] == str(fee.amount)
        assert (
            response.data["academic_year"].get("year_start")
            == fee.academic_year.year_start
        )


@pytest.mark.django_db
class TestFeeSpecificationListRetrieveAPIView:
    @apply_perms(
        "core_cms.view_fee", "core_cms.view_feespecification", client="staff_api_client"
    )
    def test_fee_specification_list(self, staff_api_client, fee_specification_factory):
        fee_specification = [fee_specification_factory() for _ in range(5)]
        url = reverse("university.core.cms:fee-specifications-list")
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert_paginated_response(response.data)
        assert len(response.data["results"]) == len(fee_specification)

    @apply_perms(
        "core_cms.view_fee", "core_cms.view_feespecification", client="staff_api_client"
    )
    def test_fee_specification_retrieve(self, staff_api_client, fee_specification):
        url = reverse(
            "university.core.cms:fee-specifications-detail",
            kwargs={"pk": fee_specification.pk},
        )
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert_fields = [
            "id",
            "code",
            "semester_from",
            "semester_to",
            "year_level_from",
            "year_level_to",
        ]

        for field in assert_fields:
            assert response.data.get(field) == getattr(fee_specification, field)

        assert len(response.data["fees"]) == fee_specification.fees.count()
        assert response.data["school"] == fee_specification.school.id
        assert response.data["subject"] == fee_specification.subject.id
        assert (
            response.data["academic_year"].get("year_start")
            == fee_specification.academic_year.year_start
        )


@pytest.mark.django_db
class TestCurriculumViewSet:
    @apply_perms("core_cms.view_curriculum", client="staff_api_client")
    def test_curriculum_list(self, staff_api_client, curriculum_factory):
        curriculum = [curriculum_factory() for _ in range(5)]
        url = reverse("university.core.cms:curriculums-list")
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert_paginated_response(response.data)
        assert len(response.data["results"]) == len(curriculum)

    @apply_perms(
        "core_cms.view_curriculum",
        "core_cms.view_curriculumperiod",
        "core_cms.view_curriculumsubject",
        client="staff_api_client",
    )
    def test_curriculum_retrieve(self, staff_api_client, curriculum):
        url = reverse(
            "university.core.cms:curriculums-detail", kwargs={"pk": curriculum.pk}
        )
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert_fields = [
            "ref_id",
            "effective_start_year",
            "effective_end_year",
            "effective_semester",
        ]

        for field in assert_fields:
            assert response.data.get(field) == getattr(curriculum, field)

        assert response.data["course"].get("id") == curriculum.course.id
        assert (
            len(response.data["curriculum_periods"])
            == curriculum.curriculum_periods.count()
        )


@pytest.mark.django_db
class TestClassViewSet:
    @apply_perms(
        "core_cms.view_class", "core_cms.view_classschedule", client="staff_api_client"
    )
    def test_class_list(self, staff_api_client, class_factory):
        klass = [class_factory() for _ in range(5)]
        url = reverse("university.core.cms:classes-list")
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert_paginated_response(response.data)
        assert len(response.data["results"]) == len(klass)

    @apply_perms(
        "core_cms.view_class", "core_cms.view_classschedule", client="staff_api_client"
    )
    def test_class_retrieve(self, staff_api_client, klass):
        url = reverse("university.core.cms:classes-detail", kwargs={"pk": klass.pk})
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert_fields = [
            "id",
            "class_code",
            "class_size",
            "is_dissolved",
            "is_crash_course",
            "is_intercollegiate",
            "is_external_class",
            "remarks",
        ]

        for field in assert_fields:
            assert response.data.get(field) == getattr(klass, field)

        assert response.data["subject"].get("id") == klass.subject.id
        assert len(response.data["class_schedules"]) == klass.class_schedules.count()
        assert response.data["units"] == klass.subject.units


@pytest.mark.django_db
class TestRoomClassificationViewSet:
    @apply_perms("core_cms.view_classification", client="staff_api_client")
    def test_room_classification_list(self, staff_api_client, classification_factory):
        classification = [classification_factory() for _ in range(5)]
        url = reverse("university.core.cms:room-classifications-list")
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert_paginated_response(response.data)
        assert len(response.data["results"]) == len(classification)

    @apply_perms("core_cms.view_classification", client="staff_api_client")
    def test_room_classification_retrieve(self, staff_api_client, classification):
        url = reverse(
            "university.core.cms:room-classifications-detail",
            kwargs={"pk": classification.pk},
        )
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert_fields = ["id", "name"]

        for field in assert_fields:
            assert response.data.get(field) == getattr(classification, field)


@pytest.mark.django_db
class TestDiscountViewSet:
    @apply_perms("core_cms.view_discount", client="staff_api_client")
    def test_discount_list(self, staff_api_client, discount_factory):
        discount = [discount_factory() for _ in range(5)]
        url = reverse("university.core.cms:discounts-list")
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert_paginated_response(response.data)
        assert len(response.data["results"]) == len(discount)

    @apply_perms(
        "core_cms.view_discount", "core_cms.view_fee", client="staff_api_client"
    )
    def test_discount_retrieve(self, staff_api_client, discount):
        url = reverse(
            "university.core.cms:discounts-detail", kwargs={"pk": discount.pk}
        )
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert_fields = [
            "id",
            "type",
            "apply_to",
            "ref_id",
            "name",
            "remarks",
            "is_confirmed",
            "category_rate_exemption",
        ]

        for field in assert_fields:
            assert response.data.get(field) == getattr(discount, field)

        assert response.data["department"].get("id") == discount.department.id
        assert len(response.data["fee_exemptions"]) == discount.fee_exemptions.count()
        assert response.data["percentage"] == str(Decimal(f"{discount.percentage:.2f}"))


@pytest.mark.django_db
class TestOpenClassPerSchoolListAPIView:
    url = reverse("university.core.cms:open-classes-per-school")

    def test_open_classes_per_school(self, staff_api_client):
        response = staff_api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestOpenClassEnrolleePerCourseListAPIView:
    url = reverse("university.core.cms:classes-enrollees-per-course")

    def test_open_classes_enrollees_per_course(self, staff_api_client):
        response = staff_api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestClassGradeStatePerSchoolListAPIView:
    url = reverse("university.core.cms:class-grade-states-per-school")

    def test_class_grades_states_per_school(self, staff_api_client):
        response = staff_api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
