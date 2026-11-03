import pytest

from university.core.accounts import services

from .factories import fake


@pytest.mark.django_db
class TestUserServices:
    def test_staff_create(self):
        password = fake.password()
        data = {
            "username": fake.user_name(),
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": fake.email(),
            "password1": password,
            "password2": password,
            "departments": [],
            "school_groups": [],
            "modules": [],
        }
        staff = services.staff_create(data)
        assert_fields = ["username", "first_name", "last_name", "email"]

        for field in assert_fields:
            assert getattr(staff, field) == data.get(field)

    def test_staff_update(self, staff, department):
        data = {
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": fake.email(),
            "departments": [department.id],
            "school_groups": [],
            "modules": [],
        }
        staff = services.staff_update(user=staff, data=data)
        assert_fields = ["first_name", "last_name", "email"]

        for field in assert_fields:
            assert getattr(staff, field) == data.get(field)

        assert staff.departments.count() == len(data.get("departments"))
        assert staff.modules.count() == len(data.get("modules"))
