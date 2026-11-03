from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from university.core.accounts.models import Department, Module, Personnel, School
from university.core.cms.models import (
    Building,
    Class,
    Classification,
    ClassSchedule,
    Course,
    Curriculum,
    CurriculumPeriod,
    CurriculumSubject,
    CurriculumSubjectRequisite,
    Discount,
    Fee,
    FeeSpecification,
    Room,
    Subject,
)
from university.core.maintenance.models import EnrollmentSchedule, ModuleConfiguration
from university.core.students.models import (
    AddSubjectRequest,
    ChangeScheduleRequest,
    EnrolledClassGrade,
    OpenClassRequest,
    Student,
    WithdrawalRequest,
)
from university.payment.models import (
    BukasTransaction,
    CashierTransaction,
    DragonpayTransaction,
    PaymentTransaction,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Creates permission sets for each Module"

    def handle(self, *args, **options):
        modules = [
            {
                "codename": "web.dashboard",
                "permissions": [],
            },
            {
                "codename": "web.student_search",
                "permissions": [
                    (Student, ["view"]),
                ],
            },
            {
                "codename": "web.grades",
                "permissions": [
                    (Student, ["view"]),
                    (EnrolledClassGrade, ["view"]),
                    (Class, ["view"]),
                ],
            },
            {
                "codename": "web.user_accounts",
                "permissions": [
                    (User, ["view", "add", "change", "delete"]),
                    (Department, ["view"]),
                    (School, ["view"]),
                    (Group, ["view"]),
                ],
            },
            {
                "codename": "web.user_roles",
                "permissions": [
                    (Group, ["view", "add", "change", "delete"]),
                ],
            },
            {
                "codename": "web.faculty",
                "permissions": [
                    (Personnel, ["view"]),
                    (Class, ["view"]),
                    (ClassSchedule, ["view"]),
                ],
            },
            {
                "codename": "web.configurations_import_data",
                "permissions": [(PaymentTransaction, ["view", "add"])],
            },
            {
                "codename": "web.configurations_module_configuration",
                "permissions": [(Module, ["view", "add"])],
            },
            {
                "codename": "web.curriculums",
                "permissions": [
                    (Curriculum, ["view"]),
                    (CurriculumPeriod, ["view"]),
                    (CurriculumSubject, ["view"]),
                    (CurriculumSubjectRequisite, ["view"]),
                ],
            },
            {
                "codename": "web.dragonpay_transactions",
                "permissions": [
                    (DragonpayTransaction, ["view"]),
                ],
            },
            {
                "codename": "web.bukas_transactions",
                "permissions": [
                    (BukasTransaction, ["view"]),
                ],
            },
            {
                "codename": "web.bank_transactions",
                "permissions": [
                    (CashierTransaction, ["view"]),
                ],
            },
            {
                "codename": "web.cashier_transactions",
                "permissions": [
                    (CashierTransaction, ["view", "change"]),
                ],
            },
            {
                "codename": "web.cms_curriculums",
                "permissions": [
                    (Curriculum, ["view", "add"]),
                ],
            },
            {
                "codename": "web.cms_courses",
                "permissions": [
                    (Course, ["view"]),
                ],
            },
            {
                "codename": "web.cms_subjects",
                "permissions": [
                    (Subject, ["view"]),
                ],
            },
            {
                "codename": "web.cms_rooms",
                "permissions": [
                    (Room, ["view"]),
                ],
            },
            {
                "codename": "web.cms_room_classifications",
                "permissions": [
                    (Classification, ["view"]),
                ],
            },
            {
                "codename": "web.cms_buildings",
                "permissions": [
                    (Building, ["view"]),
                ],
            },
            {
                "codename": "web.cms_schools",
                "permissions": [
                    (School, ["view"]),
                ],
            },
            {
                "codename": "web.cms_fees",
                "permissions": [
                    (Fee, ["view"]),
                    (FeeSpecification, ["view"]),
                ],
            },
            {
                "codename": "web.cms_classes_and_schedules",
                "permissions": [
                    (Class, ["view"]),
                    (ClassSchedule, ["view"]),
                ],
            },
            {
                "codename": "web.cms_discounts",
                "permissions": [
                    (Discount, ["view"]),
                    (Fee, ["view"]),
                ],
            },
            {
                "codename": "web.student_request_schedule_change",
                "permissions": [
                    (ChangeScheduleRequest, ["view", "change"]),
                ],
            },
            {
                "codename": "web.student_request_class_opening",
                "permissions": [
                    (OpenClassRequest, ["view", "change"]),
                ],
            },
            {
                "codename": "web.student_request_subject_addition",
                "permissions": [
                    (AddSubjectRequest, ["view", "change"]),
                ],
            },
            {
                "codename": "web.student_request_subject_withdrawal",
                "permissions": [
                    (WithdrawalRequest, ["view", "change"]),
                ],
            },
        ]

        for module_data in modules:
            module = Module.objects.filter(codename=module_data["codename"]).first()

            if not module:
                continue

            module.view_permissions.clear()
            module.add_permissions.clear()
            module.change_permissions.clear()
            module.delete_permissions.clear()

            for model, actions in module_data["permissions"]:
                ct = ContentType.objects.get_for_model(model)

                for action in actions:
                    codename = f"{action}_{model._meta.model_name}"
                    perm = Permission.objects.get(codename=codename, content_type=ct)

                    permissions = getattr(module, f"{action}_permissions")
                    permissions.add(perm)
