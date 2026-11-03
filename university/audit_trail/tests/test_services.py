import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from university.audit_trail import services
from university.audit_trail.models import TrailLog
from university.framework.events import (
    CreateModelEvent,
    DeleteModelEvent,
    EventObject,
    UpdateModelEvent,
)
from university.framework.tests import fake
from university.framework.utils import get_random_string

User = get_user_model()


@pytest.mark.django_db
class TestTrailLogCreate:
    def test_create_event_log(self, staff_user, role):
        event = CreateModelEvent("core.role_created", actor=staff_user, target=role)
        trail_log = services.handle_create(event=event)

        assert trail_log
        assert trail_log.log_id
        assert trail_log.action == TrailLog.Actions.CREATED

        user_ctype = ContentType.objects.get_for_model(User)
        assert trail_log.actor_ctype == user_ctype
        role_ctype = ContentType.objects.get_for_model(role._meta.model)
        assert trail_log.target_ctype == role_ctype

    def test_update_event_log(self, staff_user, role):
        role_before = EventObject(role)
        role.name = f"{fake.job()} - {get_random_string(length=6)}"
        role.save()
        role_after = EventObject(role)

        event = UpdateModelEvent(
            "core.role_updated",
            actor=staff_user,
            old_target=role_before,
            new_target=role_after,
        )
        trail_log = services.handle_update(event=event)

        assert trail_log
        assert trail_log.log_id
        assert trail_log.action == TrailLog.Actions.UPDATED

        user_ctype = ContentType.objects.get_for_model(User)
        assert trail_log.actor_ctype == user_ctype
        role_ctype = ContentType.objects.get_for_model(role._meta.model)
        assert trail_log.target_ctype == role_ctype

    def test_delete_event_log(self, staff_user, role):
        target = EventObject(role)
        role.delete()
        event = DeleteModelEvent("core.role_deleted", actor=staff_user, target=target)
        trail_log = services.handle_delete(event=event)

        assert trail_log
        assert trail_log.log_id
        assert trail_log.action == TrailLog.Actions.DELETED

        user_ctype = ContentType.objects.get_for_model(User)
        assert trail_log.actor_ctype == user_ctype
        role_ctype = ContentType.objects.get_for_model(role._meta.model)
        assert trail_log.target_ctype == role_ctype
