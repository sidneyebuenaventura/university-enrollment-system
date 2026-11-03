import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from university.audit_trail import selectors
from university.framework.events import EventObject

User = get_user_model()


@pytest.mark.django_db
class TestActorNameGet:
    def test_system(self):
        name = selectors.actor_name_get(actor=None)
        assert name == "System"

    def test_full_name(self, user):
        user.middle_name = None
        user.save()
        event_obj = EventObject(model_obj=user)
        name = selectors.actor_name_get(actor=event_obj)
        assert name == f"{user.last_name}, {user.first_name}"

    def test_username(self, user):
        user.first_name = ""
        user.last_name = ""
        user.save()
        event_obj = EventObject(model_obj=user)
        name = selectors.actor_name_get(actor=event_obj)
        assert name == user.username

    def test_id(self, user):
        user.first_name = ""
        user.last_name = ""
        user.username = ""
        user.save()
        event_obj = EventObject(model_obj=user)
        name = selectors.actor_name_get(actor=event_obj)
        assert name == str(user.id)


@pytest.mark.django_db
class TestActorTypeGet:
    def test_system(self):
        type = selectors.actor_type_get(actor=None)
        assert type == "System"

    def test_admin(self, personnel):
        event_obj = EventObject(model_obj=personnel.user)
        type = selectors.actor_type_get(actor=event_obj)
        assert type == User.Types.ADMIN.label

    def test_student(self, student):
        event_obj = EventObject(model_obj=student.user)
        type = selectors.actor_type_get(actor=event_obj)
        assert type == User.Types.STUDENT.label

    def test_ctype(self, personnel):
        user = personnel.user
        event_obj = EventObject(model_obj=user)
        user.delete()
        type = selectors.actor_type_get(actor=event_obj)
        user_ctype = ContentType.objects.get_for_model(User)
        assert type == str(user_ctype)


class TestTargetDifferenceGet:
    def test_no_difference(self):
        old_target = EventObject(
            data={
                "first_name": "Juan",
                "last_name": "dela Cruz",
                "email": "jdelacruz@example.com",
            }
        )
        new_target = EventObject(
            data={
                "first_name": "Juan",
                "last_name": "dela Cruz",
                "email": "jdelacruz@example.com",
            }
        )
        result = selectors.target_difference_get(
            old_target=old_target, new_target=new_target
        )
        assert not result

    def test_added_field(self):
        old_target = EventObject(
            data={
                "first_name": "Juan",
                "last_name": "dela Cruz",
                "email": "jdelacruz@example.com",
            }
        )
        mobile_number = "09123456789"
        new_target = EventObject(
            data={
                "first_name": "Juan",
                "last_name": "dela Cruz",
                "email": "jdelacruz@example.com",
                "mobile_number": mobile_number,
            }
        )
        result = selectors.target_difference_get(
            old_target=old_target, new_target=new_target
        )
        assert result.get("mobile_number")
        assert result["mobile_number"]["old"] is None
        assert result["mobile_number"]["new"] == mobile_number

    def test_removed_field(self):
        email = "jdelacruz@example.com"
        old_target = EventObject(
            data={
                "first_name": "Juan",
                "last_name": "dela Cruz",
                "email": email,
            }
        )
        new_target = EventObject(
            data={
                "first_name": "Juan",
                "last_name": "dela Cruz",
            }
        )
        result = selectors.target_difference_get(
            old_target=old_target, new_target=new_target
        )
        assert result.get("email")
        assert result["email"]["old"] == email
        assert result["email"]["new"] is None

    def test_changed_field(self):
        old_email = "jdelacruz@example.com"
        new_email = "jdcruz@example.com"

        old_target = EventObject(
            data={
                "first_name": "Juan",
                "last_name": "dela Cruz",
                "email": old_email,
            }
        )
        new_target = EventObject(
            data={
                "first_name": "Juan",
                "last_name": "dela Cruz",
                "email": new_email,
            }
        )
        result = selectors.target_difference_get(
            old_target=old_target, new_target=new_target
        )
        assert result.get("email")
        assert result["email"]["old"] == old_email
        assert result["email"]["new"] == new_email

    def test_changed_list_field(self):
        old_permissions = ["dashboard", "pre_enrollment", "settings"]
        new_permissions = ["dashboard", "enrollment", "settings"]

        old_target = EventObject(
            data={
                "first_name": "Juan",
                "last_name": "dela Cruz",
                "email": "jdelacruz@example.com",
                "permissions": old_permissions,
            }
        )
        new_target = EventObject(
            data={
                "first_name": "Juan",
                "last_name": "dela Cruz",
                "email": "jdelacruz@example.com",
                "permissions": new_permissions,
            }
        )
        result = selectors.target_difference_get(
            old_target=old_target, new_target=new_target
        )
        assert result.get("permissions")
        assert set(result["permissions"]["old"]) == set(old_permissions)
        assert set(result["permissions"]["new"]) == set(new_permissions)
        assert set(result["permissions"]["removed"]) == {"pre_enrollment"}
        assert set(result["permissions"]["added"]) == {"enrollment"}
