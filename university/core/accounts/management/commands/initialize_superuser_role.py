from django.core.management.base import BaseCommand

from university.core.accounts.constants import ReservedRole
from university.core.accounts.models import Module, Role
from university.core.accounts.services import role_update


class Command(BaseCommand):
    help = "Creates reserved core_accounts.Role"

    def handle(self, *args, **options):
        roles = [
            {
                "name": ReservedRole.SUPER_ADMIN,
                "modules": [
                    "mobile.enrollment",
                ],
            },
        ]

        for role_data in roles:
            role_name = role_data.get("name")
            role, _ = Role.objects.get_or_create(name=role_name)
            role_modules = []

            for module in Module.objects.filter(platform=Module.Platforms.WEB):
                if module:
                    role_modules.append(
                        {
                            "module": module,
                            "has_view_perm": True,
                            "has_change_perm": True,
                            "has_add_perm": True,
                            "has_delete_perm": True,
                        }
                    )

            role_update(
                role=role,
                data={
                    "name": role_name,
                    "role_modules": role_modules,
                },
            )
