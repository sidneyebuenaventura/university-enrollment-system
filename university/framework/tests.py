import functools
from decimal import Decimal

from django.contrib.auth.models import Group, Permission
from faker import Faker

fake = Faker(["en_PH", "en_US"])


def fake_amount():
    value = fake.pydecimal(
        left_digits=4,
        right_digits=2,
        positive=True,
        min_value=1000,
    )
    return Decimal(f"{value:.2f}")


def assert_exists(keys, iterable):
    for key in keys:
        assert key in iterable


def assert_paginated_response(data):
    assert_exists(["results", "next", "previous", "count", "pages"], data)


def apply_perms(*perms, client: str = None):
    """Decorator function to apply perm codes
    to authenticated user in the given API `client`.

    Parameters:
        - perms: list of permission code
        - client: variable name of an APIClient instance via fixture

    Sample Usage:

    @apply_perms("core_accounts.view_user", client="staff_api_client")
    def test_user_list(staff_api_client, user_list):
        pass

    @apply_perms("core_accounts.view_user", "core_accounts.change_user, client="staff_api_client")
    def test_user_update(staff_api_client, user_list):
        pass
    """

    def decorator(func):
        @functools.wraps(func)
        def inner(*args, **kwargs):
            api_client = kwargs.get(client)
            user = api_client.handler._force_user
            applied_permissions = []

            role = Group.objects.create(name="Sample role")

            for perm_name in perms:
                app_label, codename = perm_name.split(".")
                permission = Permission.objects.get(
                    content_type__app_label=app_label, codename=codename
                )
                applied_permissions.append(permission)

            role.permissions.set(applied_permissions)
            user.groups.add(role)

            return_val = func(*args, **kwargs)

            user.groups.remove(role)
            role.delete()
            return return_val

        return inner

    return decorator
