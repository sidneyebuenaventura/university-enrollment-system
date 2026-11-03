from typing import Union

from django.db import transaction

from university.framework.events import CreateModelEvent, DeleteModelEvent, UpdateModelEvent

from . import selectors
from .models import TrailLog


def trail_log_create(
    event: Union[CreateModelEvent, UpdateModelEvent, DeleteModelEvent],
    action: TrailLog.Actions,
) -> TrailLog:
    actor = event.actor

    if event.type in ["create", "delete"]:
        target = event.target
        meta = {"model": target.data}
    elif event.type == "update":
        old_target = event.old_target
        new_target = event.new_target
        target = new_target
        meta = {"changes": selectors.target_difference_get(old_target, new_target)}
    else:
        return

    with transaction.atomic():
        trail_log = TrailLog.objects.create(
            actor_name=selectors.actor_name_get(actor),
            actor_type=selectors.actor_type_get(actor),
            actor_ctype_id=actor.ctype_data.get("id"),
            actor_id=actor.data.get("id"),
            target_ctype_id=target.ctype_data.get("id"),
            target_id=target.data.get("id"),
            action=action,
            meta=meta,
            datetime=event.data.get("timestamp"),
        )
        trail_log.generate_log_id()

    return trail_log


def handle_create(event: CreateModelEvent) -> TrailLog:
    return trail_log_create(event=event, action=TrailLog.Actions.CREATED)


def handle_update(event: UpdateModelEvent) -> TrailLog:
    return trail_log_create(event=event, action=TrailLog.Actions.UPDATED)


def handle_delete(event: DeleteModelEvent) -> TrailLog:
    return trail_log_create(event=event, action=TrailLog.Actions.DELETED)
