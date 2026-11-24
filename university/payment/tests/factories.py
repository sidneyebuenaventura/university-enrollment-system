from datetime import timedelta
from decimal import Decimal

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory
from pytest_factoryboy import LazyFixture, register

from university.core.accounts.tests.factories import SchoolFactory
from university.core.students.tests.factories import EnrollmentFactory
from university.framework.tests import fake, fake_amount
from university.payment import models


@register(enrollment=LazyFixture("base_enrollment"))
class StatementOfAccountFactory(DjangoModelFactory):
    enrollment = factory.SubFactory(EnrollmentFactory)
    user = factory.SelfAttribute("enrollment.student.user")
    total_amount = factory.LazyFunction(fake_amount)
    min_amount = factory.LazyAttribute(
        lambda o: (o.total_amount * Decimal("0.35")).quantize(Decimal("0.01"))
    )
    min_amount_due_date = factory.LazyFunction(
        lambda: timezone.now() + timedelta(days=30)
    )

    class Meta:
        model = models.StatementOfAccount


@register
class AccountTransactionFactory(DjangoModelFactory):
    soa = factory.SubFactory(StatementOfAccountFactory)
    student = factory.SelfAttribute("soa.enrollment.student")
    amount = factory.LazyFunction(fake_amount)
    description = factory.LazyFunction(fake.sentence)

    class Meta:
        model = models.AccountTransaction


@register
class DragonpayChannelFactory(DjangoModelFactory):
    proc_id = factory.LazyFunction(lambda: fake.pystr(4, 4).upper())
    description = factory.LazyFunction(lambda: fake.company())
    addon_fixed = Decimal(0)

    class Meta:
        model = models.DragonpayChannel


@register
class DragonpayKeyFactory(DjangoModelFactory):
    school = factory.SubFactory(SchoolFactory)
    merchant_id = factory.LazyFunction(lambda: fake.pystr(8, 8).upper())
    merchant_password = factory.LazyFunction(fake.password)

    class Meta:
        model = models.DragonpayKey


@register
class DragonpayTransactionFactory(DjangoModelFactory):
    soa = factory.SubFactory(StatementOfAccountFactory)
    channel = factory.SubFactory(DragonpayChannelFactory)
    amount = factory.LazyFunction(fake_amount)

    class Meta:
        model = models.DragonpayTransaction


@register
class BukasTransactionFactory(DjangoModelFactory):
    soa = factory.SubFactory(StatementOfAccountFactory)

    class Meta:
        model = models.BukasTransaction


@register
class OverTheCounterTransactionFactory(DjangoModelFactory):
    soa = factory.SubFactory(StatementOfAccountFactory)
    bank = factory.Iterator(models.OverTheCounterTransaction.Banks)

    class Meta:
        model = models.OverTheCounterTransaction


@register
class CashierTransactionFactory(DjangoModelFactory):
    soa = factory.SubFactory(StatementOfAccountFactory)

    class Meta:
        model = models.CashierTransaction
