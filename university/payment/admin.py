from django.contrib import admin
from django.forms import ModelForm, PasswordInput
from django.http import HttpResponseRedirect
from django.urls import reverse
from django_object_actions import DjangoObjectActions
from polymorphic.admin import (
    PolymorphicChildModelAdmin,
    PolymorphicChildModelFilter,
    PolymorphicInlineSupportMixin,
    PolymorphicParentModelAdmin,
    StackedPolymorphicInline,
)

from . import models


class PaymentTransactionInline(StackedPolymorphicInline):
    class DragonpayTransactionInline(StackedPolymorphicInline.Child):
        model = models.DragonpayTransaction

    class BukasTransactionInline(StackedPolymorphicInline.Child):
        model = models.BukasTransaction

    class OverTheCounterTransactionInline(StackedPolymorphicInline.Child):
        model = models.OverTheCounterTransaction

    class CashierTransactionInline(StackedPolymorphicInline.Child):
        model = models.CashierTransaction
        raw_id_fields = ("processed_by",)

    model = models.PaymentTransaction
    child_inlines = (
        DragonpayTransactionInline,
        BukasTransactionInline,
        OverTheCounterTransactionInline,
        CashierTransactionInline,
    )


class StatementLineInline(admin.TabularInline):
    model = models.StatementLine


@admin.register(models.StatementOfAccount)
class StatementOfAccountAdmin(PolymorphicInlineSupportMixin, admin.ModelAdmin):
    list_display = ["user", "total_amount", "min_amount"]
    raw_id_fields = ("user", "enrollment")
    ordering = ("-created_at",)
    inlines = (StatementLineInline, PaymentTransactionInline)


@admin.register(models.StatementLineCategory)
class StatementLineCategoryAdmin(admin.ModelAdmin):
    list_display = ["soa", "label"]
    raw_id_fields = ("soa",)
    inlines = (StatementLineInline,)


@admin.register(models.AccountTransaction)
class AccountTransactionAdmin(admin.ModelAdmin):
    list_display = ["id", "student", "soa", "amount", "description"]
    raw_id_fields = ("student", "soa")


@admin.register(models.PaymentTransaction)
class PaymentTransactionParentAdmin(DjangoObjectActions, PolymorphicParentModelAdmin):
    list_display = ["payment_id", "soa", "polymorphic_ctype"]
    child_models = (
        models.DragonpayTransaction,
        models.BukasTransaction,
        models.OverTheCounterTransaction,
        models.CashierTransaction,
    )
    list_filter = (PolymorphicChildModelFilter,)
    changelist_actions = (
        "generate_dragonpay_settlement_file",
        "generate_cashier_settlement_file",
        "generate_journal_voucher_file",
    )

    def generate_dragonpay_settlement_file(modeladmin, request, queryset):
        url = reverse("university.payment:dragonpay-settlements-test-file-generate")
        return HttpResponseRedirect(url)

    def generate_cashier_settlement_file(modeladmin, request, queryset):
        url = reverse("university.payment:cashier-settlements-test-file-generate")
        return HttpResponseRedirect(url)

    def generate_journal_voucher_file(modeladmin, request, queryset):
        url = reverse("university.payment:journal-vouchers-test-file-generate")
        return HttpResponseRedirect(url)


class PaymentTransactionChildAdmin(PolymorphicChildModelAdmin):
    base_model = models.PaymentTransaction


@admin.register(models.DragonpayTransaction)
class DragonpayTransactionAdmin(PaymentTransactionChildAdmin):
    pass


@admin.register(models.DragonpayChannel)
class DragonpayChannelAdmin(admin.ModelAdmin):
    list_display = ["proc_id", "description"]


class DragonpayKeyForm(ModelForm):
    class Meta:
        model = models.DragonpayKey
        fields = "__all__"
        widgets = {
            "merchant_password": PasswordInput(),
        }


@admin.register(models.DragonpayKey)
class DragonpayKeyAdmin(admin.ModelAdmin):
    list_display = ["merchant_id", "school"]
    form = DragonpayKeyForm


@admin.register(models.BukasTransaction)
class BukasTransactionAdmin(PaymentTransactionChildAdmin):
    pass


@admin.register(models.OverTheCounterTransaction)
class OverTheCounterTransactionAdmin(PaymentTransactionChildAdmin):
    pass


@admin.register(models.CashierTransaction)
class CashierTransactionAdmin(PaymentTransactionChildAdmin):
    raw_id_fields = ("processed_by",)
