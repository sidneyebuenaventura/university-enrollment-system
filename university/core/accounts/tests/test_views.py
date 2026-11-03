import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

from university.core.accounts import models
from university.framework.tests import apply_perms, assert_paginated_response, fake

User = get_user_model()


@pytest.mark.django_db
class TestStaffViewSet:
    @apply_perms("core_accounts.view_user", client="staff_api_client")
    def test_staffs_list(self, staff_api_client, staff_factory):
        staffs = [staff_factory() for _ in range(5)]
        url = reverse("university.core.accounts:staffs-list")
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert_paginated_response(response.data)
        assert len(response.data["results"]) == len(staffs) + 1  # in staff_api_client

    @apply_perms(
        "core_accounts.add_user",
        "core_accounts.view_department",
        "core_accounts.view_school",
        "auth.view_group",
        client="staff_api_client",
    )
    def test_staffs_create(
        self, staff_api_client, department, school, role_factory, module
    ):
        roles = [role_factory() for _ in range(5)]
        password = fake.password()
        data = {
            "username": fake.user_name(),
            "email": fake.email(),
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "password1": password,
            "password2": password,
            "departments": [department.id],
            "modules": [module.id],
            "school_groups": [
                {
                    "school": school.id,
                    "roles": [role.id for role in roles],
                }
            ],
        }

        url = reverse("university.core.accounts:staffs-list")
        response = staff_api_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert_fields = ["username", "email", "first_name", "last_name"]

        for field in assert_fields:
            assert response.data.get(field) == data.get(field)

        user = User.objects.get(pk=response.data.get("id"))
        assert user.username == data.get("username")
        assert user.departments.count() == len(data.get("departments"))
        assert user.departments.first().id == department.id
        assert user.school_groups.count() == len(data.get("school_groups"))
        assert user.modules.count() == len(data.get("modules"))

        school_group = user.school_groups.first()
        assert school_group.school.id == school.id
        assert school_group.roles.count() == len(data["school_groups"][0]["roles"])

    @apply_perms(
        "core_accounts.view_user",
        "core_accounts.view_department",
        "core_accounts.view_school",
        "auth.view_group",
        client="staff_api_client",
    )
    def test_staffs_retrieve(self, staff_api_client, staff):
        url = reverse("university.core.accounts:staffs-detail", kwargs={"pk": staff.id})
        response = staff_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert_fields = ["id", "username", "first_name", "last_name", "status"]

        for field in assert_fields:
            assert response.data.get(field) == getattr(staff, field)

        assert len(response.data.get("departments")) == staff.departments.count()
        assert len(response.data.get("school_groups")) == staff.school_groups.count()

    @apply_perms(
        "core_accounts.change_user",
        "core_accounts.view_department",
        "core_accounts.view_school",
        "auth.view_group",
        client="staff_api_client",
    )
    def test_staffs_update(
        self, staff_api_client, staff, department, school, role_factory, module
    ):
        roles = [role_factory() for _ in range(5)]
        data = {
            "email": staff.email,
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "departments": list(staff.departments.values_list("id", flat=True)),
            "modules": list(staff.modules.values_list("id", flat=True)),
            "school_groups": [
                {
                    "school": school.id,
                    "roles": [role.id for role in roles],
                }
            ],
        }

        # Add department
        data["departments"].append(department.id)

        url = reverse("university.core.accounts:staffs-detail", kwargs={"pk": staff.id})
        response = staff_api_client.patch(url, data)

        staff.refresh_from_db()
        assert response.status_code == status.HTTP_200_OK
        assert_fields = ["id", "username", "first_name", "last_name", "status"]

        for field in assert_fields:
            assert response.data.get(field) == getattr(staff, field)

        assert len(data.get("departments")) == staff.departments.count()
        assert len(response.data.get("school_groups")) == staff.school_groups.count()
        assert len(response.data.get("modules")) == staff.modules.count()

    @apply_perms(
        "core_accounts.change_user",
        "core_accounts.view_department",
        "core_accounts.view_school",
        "auth.view_group",
        client="staff_api_client",
    )
    def test_staffs_partial_update(self, staff_api_client, staff):
        data = {
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
        }

        url = reverse("university.core.accounts:staffs-detail", kwargs={"pk": staff.id})
        response = staff_api_client.patch(url, data)

        staff.refresh_from_db()
        assert response.status_code == status.HTTP_200_OK
        assert data.get("first_name") == staff.first_name
        assert data.get("last_name") == staff.last_name

    @apply_perms("core_accounts.delete_user", client="staff_api_client")
    def test_staffs_destroy(self, staff_api_client, staff):
        url = reverse("university.core.accounts:staffs-detail", kwargs={"pk": staff.id})
        response = staff_api_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not User.objects.filter(pk=staff.id, is_active=True).exists()


@pytest.mark.django_db
class TestModuleListAPIView:
    def test_modules_list(self, staff_api_client, module_factory):
        modules = [module_factory() for _ in range(5)]
        url = reverse("university.core.accounts:modules-list")
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == len(modules)


@pytest.mark.django_db
class TestRoleViewSet:
    @apply_perms("auth.view_group", client="staff_api_client")
    def test_roles_list(self, staff_api_client, role_factory):
        roles = [role_factory() for _ in range(5)]
        url = reverse("university.core.accounts:roles-list")
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert_paginated_response(response.data)
        assert (
            len(response.data["results"]) == len(roles) + 1
        )  # NOTE: count the created user role

    @apply_perms("auth.add_group", client="staff_api_client")
    def test_roles_create(self, staff_api_client, module):
        url = reverse("university.core.accounts:roles-list")

        data = {
            "name": fake.job(),
            "role_modules": [
                {
                    "module": module.id,
                    "has_view_perm": True,
                    "has_change_perm": True,
                }
            ],
        }

        response = staff_api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED

        role = models.Role.admin_objects.get(pk=response.data.get("id"))
        assert role.name == data.get("name")
        assert role.rolemodule_set.count() == len(data.get("role_modules"))

    @apply_perms("auth.view_group", client="staff_api_client")
    def test_roles_retrieve(self, staff_api_client, role):
        url = reverse("university.core.accounts:roles-detail", kwargs={"pk": role.id})
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data.get("name") == role.name

    @apply_perms("auth.change_group", client="staff_api_client")
    def test_roles_update(self, staff_api_client, role, module):
        data = {
            "name": fake.job(),
            "role_modules": [
                {
                    "module": role_module.module.id,
                    "has_view_perm": role_module.has_view_perm,
                    "has_change_perm": role_module.has_change_perm,
                }
                for role_module in role.rolemodule_set.all()
            ],
        }

        # Add role module
        data["role_modules"].append(
            {
                "module": module.id,
                "has_view_perm": True,
                "has_change_perm": True,
            }
        )

        url = reverse("university.core.accounts:roles-detail", kwargs={"pk": role.id})
        response = staff_api_client.put(url, data)

        role.refresh_from_db()
        assert response.status_code == status.HTTP_200_OK
        assert role.name == data.get("name")
        assert role.rolemodule_set.count() == len(data.get("role_modules"))

    @apply_perms("auth.change_group", client="staff_api_client")
    def test_roles_partial_update(self, staff_api_client, role):
        data = {
            "name": fake.job(),
        }

        url = reverse("university.core.accounts:roles-detail", kwargs={"pk": role.id})
        response = staff_api_client.patch(url, data)

        role.refresh_from_db()
        assert response.status_code == status.HTTP_200_OK
        assert data.get("name") == role.name

    @apply_perms("auth.delete_group", client="staff_api_client")
    def test_roles_destory(self, staff_api_client, role):
        url = reverse("university.core.accounts:roles-detail", kwargs={"pk": role.id})
        response = staff_api_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not models.Role.admin_objects.filter(pk=role.id).exists()


@pytest.mark.django_db
class TestSchoolViewSet:
    @apply_perms("core_accounts.view_school", client="staff_api_client")
    def test_schools_list(self, staff_api_client, school_factory):
        schools = [school_factory() for _ in range(5)]
        url = reverse("university.core.accounts:schools-list")
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert_paginated_response(response.data)
        assert len(response.data["results"]) == len(schools)

    @apply_perms("core_accounts.view_school", client="staff_api_client")
    def test_schools_retrieve(self, staff_api_client, school):
        url = reverse(
            "university.core.accounts:schools-detail", kwargs={"pk": school.id}
        )
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data.get("name") == school.name


@pytest.mark.django_db
class TestDepartmentViewSet:
    @apply_perms("core_accounts.view_department", client="staff_api_client")
    def test_departments_list(self, staff_api_client, department_factory):
        departments = [department_factory() for _ in range(5)]
        url = reverse("university.core.accounts:departments-list")
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert_paginated_response(response.data)
        assert len(response.data["results"]) == len(departments)

    @apply_perms("core_accounts.view_department", client="staff_api_client")
    def test_departments_retrieve(self, staff_api_client, department):
        url = reverse(
            "university.core.accounts:departments-detail", kwargs={"pk": department.id}
        )
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data.get("name") == department.name


@pytest.mark.django_db
class TestFacultyViewSet:
    @apply_perms("core_accounts.view_personnel", client="staff_api_client")
    def test_faculty_list(self, staff_api_client, faculty_factory):
        faculty = [faculty_factory() for _ in range(5)]
        url = reverse("university.core.accounts:faculty-list")
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert_paginated_response(response.data)
        assert len(response.data["results"]) == len(faculty)

    @apply_perms(
        "core_accounts.view_personnel",
        "core_cms.view_class",
        "core_cms.view_classschedule",
        client="staff_api_client",
    )
    def test_faculty_retrieve(self, staff_api_client, faculty):
        url = reverse(
            "university.core.accounts:faculty-detail", kwargs={"pk": faculty.id}
        )
        response = staff_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        user_assert_fields = ["id", "username", "first_name", "last_name", "status"]
        user_data = getattr(faculty, "user")

        for field in user_assert_fields:
            response.data.get("user").get(field) == getattr(user_data, field)

        assert_fields = [
            "ref_id",
            "emp_id",
            "last_name",
            "first_name",
            "last_name",
            "rank",
            "category",
            "employment_type",
            "employment_date",
        ]
        for field in assert_fields:
            response.data.get(field) == getattr(faculty, field)

        assert (
            len(response.data.get("user").get("departments"))
            == faculty.user.departments.count()
        )
        assert (
            len(response.data.get("subject_classes")) == faculty.subject_classes.count()
        )


@pytest.mark.django_db
class TestAcademicYearCurrentRetrieveAPI:
    def test_academic_year_current_retrieve(self, staff_api_client, academic_year):
        url = reverse("university.core.accounts:academic-years-current")
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert_fields = ["year_start", "year_end", "date_start", "date_end"]

        for field in assert_fields:
            response.data.get(field) == getattr(academic_year, field)


@pytest.mark.django_db
class TestStaffProfileRetrieveAPI:
    def test_staff_profile_retrieve(self, staff_api_client, staff_user):
        url = reverse("university.core.accounts:profile")
        response = staff_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert_fields = ["username", "email"]

        for field in assert_fields:
            response.data.get(field) == getattr(staff_user, field)

        len(response.data.get("roles")) == staff_user.groups.count()
