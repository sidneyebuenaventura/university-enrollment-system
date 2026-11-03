from django.core.management.base import BaseCommand

from university.core.accounts.constants import ReservedRole
from university.core.accounts.models import Module, Role
from university.core.accounts.services import role_update


class Command(BaseCommand):
    help = "Creates reserved core_accounts.Role"

    def handle(self, *args, **options):
        roles = [
            {
                "name": ReservedRole.STUDENT,
                "modules": [
                    "mobile.dashboard",
                    "mobile.soa",
                    "mobile.curriculum_checklist",
                    "mobile.student_information",
                    "mobile.request_submission",
                ],
            },
            {
                "name": ReservedRole.STUDENT_PRE_ENROLLMENT,
                "modules": [
                    "mobile.pre_enrollment",
                ],
            },
            {
                "name": ReservedRole.STUDENT_ENROLLMENT,
                "modules": [
                    "mobile.enrollment",
                ],
            },
        ]

        for role_data in roles:
            role_name = role_data.get("name")
            role, _ = Role.objects.get_or_create(name=role_name)
            role_modules = []

            for module_codename in role_data.get("modules"):
                module = Module.objects.filter(codename=module_codename).first()

                if module:
                    role_modules.append(
                        {
                            "module": module,
                            "has_view_perm": True,
                        }
                    )

            role_update(
                role=role,
                data={
                    "name": role_name,
                    "role_modules": role_modules,
                },
            )
