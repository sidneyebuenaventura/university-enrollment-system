import importlib
from typing import Union

import structlog
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core import serializers
from django.db.models import Model
from django.utils import timezone
from kombu import Connection, Exchange, Queue
from kombu.mixins import ConsumerMixin
from kombu.pools import producers
from rest_framework.serializers import ModelSerializer
from sentry_sdk import capture_exception

log = structlog.get_logger(__name__)


def _filter_serialized_data(data):
    exclude_fields = ["password"]
    filtered_data = {}

    for field, value in data.items():
        if field in exclude_fields:
            continue
        elif isinstance(value, dict):
            filtered_data[field] = _filter_serialized_data(value)
        else:
            filtered_data[field] = value

    return filtered_data


def _serialize_model(model_obj):
    class ProxySerializer(ModelSerializer):
        class Meta:
            model = model_obj._meta.model
            fields = "__all__"
            depth = 1

    data = ProxySerializer(model_obj).data
    return _filter_serialized_data(data)


class EventNameError(Exception):
    pass


class Event:
    def __init__(self, name, data=None, **kwargs):
        name_split = name.split(".")

        if len(name_split) != 2:
            raise EventNameError(
                "Incorrect event name. Allowed format: service_name.event_name"
            )

        self.name = name_split[1]
        self.service_name = name_split[0]
        self.data = data or {}
        self.data.update(kwargs)

        if not "timestamp" in self.data:
            self.data["timestamp"] = timezone.now()

        if not "type" in self.data:
            self.data["type"] = "event"

        self.timestamp = self.data["timestamp"]
        self.type = self.data["type"]

    def __str__(self):
        return self.full_name

    def __repr__(self):
        return f"<university.Event {self.full_name}>"

    @classmethod
    def from_dict(cls, msg_body):
        data = msg_body.get("data")
        event_type = data.get("type")

        type_map = {
            "_generic": GenericEvent,
            "generic": GenericModelEvent,
            "create": CreateModelEvent,
            "update": UpdateModelEvent,
            "delete": DeleteModelEvent,
        }
        event_cls = type_map.get(event_type)

        if event_cls:
            return event_cls.from_dict(msg_body)

        return cls(msg_body.get("event"), data=data)

    @property
    def full_name(self):
        return f"{self.service_name}.{self.name}"

    def publish(self):
        # Find event bus instance
        service_events = importlib.import_module(
            f"university.{self.service_name}.events"
        )
        service_events.bus.publish(self)

    def to_dict(self):
        return {
            "event": self.full_name,
            "data": self.data,
        }


class EventObject:
    def __init__(
        self, model_obj: Model = None, data: dict = None, ctype_data: dict = None
    ):
        if model_obj:
            self.data = _serialize_model(model_obj)
            ctype = ContentType.objects.get_for_model(model_obj._meta.model)
            self.ctype_data = _serialize_model(ctype)
        else:
            self.data = data
            self.ctype_data = ctype_data

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            data=data.get("data"),
            ctype_data=data.get("ctype_data"),
        )

    def to_dict(self):
        return {
            "data": self.data,
            "ctype_data": self.ctype_data,
        }

    def get_from_db(self):
        if hasattr(self, "object"):
            return self.object

        ctype = self.get_ctype()
        model_cls = ctype.model_class()
        obj = model_cls.objects.filter(pk=self.data.get("id")).first()
        # Object cache
        self.object = obj
        return obj

    def get_ctype(self):
        if hasattr(self, "ctype"):
            return self.ctype
        self.ctype = ContentType.objects.get(pk=self.ctype_data.get("id"))
        return self.ctype


class GenericEvent(Event):
    """Deprecated. Use GenericModelEvent instead."""

    def __init__(self, name, obj, **kwargs):
        self.object = obj
        data = {
            "object": serializers.serialize("json", [obj]),
            "type": "_generic",
        }
        super().__init__(name, data=data, **kwargs)

    @classmethod
    def from_dict(cls, msg_body):
        data = msg_body.get("data")
        obj = list(serializers.deserialize("json", data.pop("object")))[0]
        return cls(msg_body.get("event"), obj.object, **data)


class GenericModelEvent(Event):
    def __init__(self, name: str, object: Union[Model, EventObject], **kwargs):
        if isinstance(object, Model):
            object = EventObject(object)

        self.object = object
        data = {
            "object": object.to_dict(),
            "type": "generic",
        }
        super().__init__(name, data=data, **kwargs)

    @classmethod
    def from_dict(cls, msg_body):
        data = msg_body.get("data")
        object_data = data.pop("object")
        object = EventObject.from_dict(object_data)
        return cls(msg_body.get("event"), object=object, **data)


class CreateDeleteEventMixin:
    def __init__(
        self,
        name: str,
        actor: Union[Model, EventObject] = None,
        target: Union[Model, EventObject] = None,
        **kwargs,
    ):
        if isinstance(actor, Model):
            actor = EventObject(actor)

        if isinstance(target, Model):
            target = EventObject(target)

        self.actor = actor
        self.target = target

        actor_data = None
        target_data = None

        if actor:
            actor_data = actor.to_dict()

        if target:
            target_data = target.to_dict()

        data = {
            "actor": actor_data,
            "target": target_data,
            "type": self.type,
        }
        super().__init__(name, data=data, **kwargs)

    @classmethod
    def from_dict(cls, msg_body):
        data = msg_body.get("data")
        actor = data.pop("actor")
        target = data.pop("target")

        if actor:
            actor = EventObject.from_dict(actor)

        if target:
            target = EventObject.from_dict(target)

        return cls(
            name=msg_body.get("event"),
            actor=actor,
            target=target,
            **data,
        )


class CreateModelEvent(CreateDeleteEventMixin, Event):
    type = "create"


class DeleteModelEvent(CreateDeleteEventMixin, Event):
    type = "delete"


class UpdateModelEvent(Event):
    def __init__(
        self,
        name: str,
        actor: Union[Model, EventObject] = None,
        old_target: Union[Model, EventObject] = None,
        new_target: Union[Model, EventObject] = None,
        **kwargs,
    ):
        if isinstance(actor, Model):
            actor = EventObject(actor)

        if isinstance(old_target, Model):
            old_target = EventObject(old_target)

        if isinstance(new_target, Model):
            new_target = EventObject(new_target)

        self.actor = actor
        self.old_target = old_target
        self.new_target = new_target

        actor_data = None
        old_target_data = None
        new_target_data = None

        if actor:
            actor_data = actor.to_dict()

        if old_target:
            old_target_data = old_target.to_dict()

        if new_target:
            new_target_data = new_target.to_dict()

        data = {
            "actor": actor_data,
            "old_target": old_target_data,
            "new_target": new_target_data,
            "type": "update",
        }
        super().__init__(name, data=data, **kwargs)

    @classmethod
    def from_dict(cls, msg_body):
        data = msg_body.get("data")
        actor = data.pop("actor")
        old_target = data.pop("old_target")
        new_target = data.pop("new_target")

        if actor:
            actor = EventObject.from_dict(actor)

        if old_target:
            old_target = EventObject.from_dict(old_target)

        if new_target:
            new_target = EventObject.from_dict(new_target)

        return cls(
            msg_body.get("event"),
            actor=actor,
            old_target=old_target,
            new_target=new_target,
            **data,
        )


class EventConsumer(ConsumerMixin):
    def __init__(self, service_name, services, connection):
        self.service_name = service_name
        self.services = services
        self.connection = connection
        self.connect_max_retries = 3

        exchange = Exchange(settings.EVENT_GLOBAL_EXCHANGE, "fanout", durable=True)
        self.queue = Queue(
            f"university.{service_name}", exchange=exchange, routing_key=service_name
        )

    def get_consumers(self, Consumer, channel):
        consumer = Consumer(
            queues=[self.queue],
            accept=["json"],
            callbacks=[self.process],
            tag_prefix=self.service_name,
        )
        return [consumer]

    def execute_handler(self, handler, event):
        try:
            handler(event=event)
        except Exception as e:
            capture_exception(e)
            log.exception(e)

    def process(self, body, message):
        event = Event.from_dict(body)
        handler_name = f"handle_{event.name}"
        handler = getattr(self.services, handler_name, None)

        if not handler and event.type in ["create", "update", "delete"]:
            # Generic handling for model events
            handler_name = f"handle_{event.type}"
            handler = getattr(self.services, handler_name, None)

        if handler:
            self.execute_handler(handler, event)

        message.ack()


class EventBus:
    def __init__(self, service_name):
        self.service_name = service_name
        self.connection = Connection(settings.EVENT_BROKER_URL)
        self.exchange = Exchange(settings.EVENT_GLOBAL_EXCHANGE, "fanout", durable=True)

    def publish(self, event):
        with producers[self.connection].acquire(block=True) as producer:
            producer.publish(
                event.to_dict(),
                serializer="json",
                exchange=self.exchange,
                declare=[self.exchange],
                retry=True,
            )


class EventPublisher:
    def generic(self, name, object, **data):
        """Shortcut to publish `GenericModelEvent`s"""
        event = GenericModelEvent(name, object=object, **data)
        event.publish()

    def create(self, name, actor, target, **data):
        """Shortcut to publish `CreateModelEvent`s"""
        event = CreateModelEvent(name, actor=actor, target=target, **data)
        event.publish()

    def update(self, name, actor, old_target, new_target, **data):
        """Shortcut to publish `UpdateModelEvent`s"""
        event = UpdateModelEvent(
            name, actor=actor, old_target=old_target, new_target=new_target, **data
        )
        event.publish()

    def delete(self, name, actor, target, **data):
        """Shortcut to publish `DeleteModelEvent`s"""
        event = DeleteModelEvent(name, actor=actor, target=target, **data)
        event.publish()


event_publisher = EventPublisher()
