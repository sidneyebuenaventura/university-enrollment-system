from datetime import timedelta

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory
from pytest_factoryboy import register

from university.core.accounts.constants import MobileModule
from university.core.accounts.models import Module
from university.core.accounts.tests.factories import ModuleFactory
from university.core.maintenance import models


@register
class ModuleConfigurationFactory(DjangoModelFactory):
    module = factory.SubFactory(
        ModuleFactory,
        platform=Module.Platforms.MOBILE,
        codename=MobileModule.ENROLLMENT,
    )
    description = "Enrollment"

    class Meta:
        model = models.ModuleConfiguration


@register
class EnrollmentScheduleFactory(DjangoModelFactory):
    config = factory.SubFactory(ModuleConfigurationFactory)
    start_datetime = factory.LazyFunction(lambda: timezone.now() + timedelta(hours=1))
    end_datetime = factory.LazyAttribute(lambda o: o.start_datetime + timedelta(days=7))
    year_level = 1

    class Meta:
        model = models.EnrollmentSchedule
