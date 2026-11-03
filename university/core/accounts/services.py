from datetime import date
from typing import Dict, List

from django.contrib.auth.tokens import default_token_generator as token_generator
from django.db import transaction
from django.db.models import Q
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode as uid_decoder
from rest_framework import exceptions
from rest_framework.exceptions import ValidationError

from university.core import events
from university.framework.events import event_publisher
from university.framework.utils import get_random_string

from . import selectors
from .models import (
    Department,
    Module,
    PasswordHistory,
    Personnel,
    Role,
    User,
    UserSchoolGroup,
)


@transaction.atomic
def staff_create(data: Dict) -> User:
    _data = data.copy()

    department_ids = _data.pop("departments")
    school_groups = _data.pop("school_groups")
    modules = _data.pop("modules")
    password = _data.pop("password1")
    _data.pop("password2")

    user = User.objects.create(is_staff=True, **_data)
    user.set_password(password)
    user.save()

    # NOTE: Temporary until there is a profile creation in admin portal
    if user.is_staff:
        personnel_data = {"first_name": user.first_name, "last_name": user.last_name}
        personnel_create(user=user, data=personnel_data)

    user_department_create(department_ids=department_ids, user=user)
    user_school_group_create(school_groups=school_groups, user=user)
    user_module_create(user=user, modules=modules)

    return user


@transaction.atomic
def user_module_create(*, user: User, modules=list[Module]) -> None:
    user.modules.clear()

    for module in modules:
        user.modules.add(module)

    return


@transaction.atomic
def personnel_create(*, user: User, data=Dict) -> Personnel:
    personnel = Personnel.objects.create(user=user, **data)
    return personnel


@transaction.atomic
def staff_update(*, user: User, data: Dict) -> User:
    _data = data.copy()

    department_ids = _data.pop("departments", None)
    school_groups = _data.pop("school_groups", None)
    modules = _data.pop("modules", None)

    user.__dict__.update(**_data)
    user.save()

    # NOTE: Temporary until there is a profile update in admin portal
    if user.is_staff and user.type == User.Types.ADMIN:
        personnel_data = {"first_name": user.first_name, "last_name": user.last_name}
        personnel_update(user=user, data=personnel_data)

    if department_ids is not None:
        user_department_create(department_ids=department_ids, user=user)

    if school_groups:
        user_school_group_create(school_groups=school_groups, user=user)

    if modules is not None:
        user_module_create(user=user, modules=modules)

    return user


@transaction.atomic
def personnel_update(*, user: User, data=Dict) -> Personnel:
    user.personnel.__dict__.update(**data)
    user.personnel.save()

    return user.personnel


@transaction.atomic
def staff_delete(*, user: User) -> None:
    if user.type == User.Types.ADMIN:
        personnel_delete(user=user)

    user.departments.clear()
    user.modules.clear()

    user.soft_delete(commit=False)
    user.set_unusable_password()
    user.username = f"DELETED-{user.username}-{get_random_string()}"
    user.email = ""
    user.is_active = False
    user.save()


@transaction.atomic
def personnel_delete(*, user: User) -> None:
    user.personnel.soft_delete()


def user_role_create(*, roles: List[Role], user: User) -> None:
    user.groups.add(*roles)


def user_department_create(*, department_ids: List[int], user: User) -> None:
    user.departments.clear()

    for id in department_ids:
        department = Department.objects.filter(id=id).first()
        if department:
            department.users.add(user)
        else:
            raise ValidationError("Invalid Department ID")


def user_role_remove(*, role_key: str, user: User):
    role = Role.objects.filter(name=role_key).first()

    if role:
        user.groups.remove(role)


def user_password_history_create(
    *,
    user: User,
    hashed_password: str = None,
    type: str = PasswordHistory.Types.CHANGED,
):
    return user.password_histories.create(value=hashed_password, type=type)


def user_password_set(*, user: User, password: str):
    user_password_change(user=user, password=password)

    user.is_first_login = False
    user.save()


def user_password_change(*, user: User, password: str):
    password_history = selectors.user_password_history_get(user=user, password=password)

    if password_history:
        error_msg = "Using your last 2 passwords is not allowed."
        raise exceptions.ValidationError({"detail": error_msg})

    first_name = user.first_name
    last_name = user.last_name
    email_name = None

    if user.email:
        email_name = user.email.split("@")[0]

    if user.type == User.Types.STUDENT:
        student = user.student
        first_name = student.first_name
        last_name = student.last_name

        if student.email:
            email_name = student.email.split("@")[0]

    if first_name.lower() in password.lower():
        error_msg = "The password is too similar to the first name."
        raise exceptions.ValidationError({"detail": error_msg})

    if last_name.lower() in password.lower():
        error_msg = "The password is too similar to the last name."
        raise exceptions.ValidationError({"detail": error_msg})

    if email_name and email_name.lower() in password.lower():
        error_msg = "The password is too similar to the email."
        raise exceptions.ValidationError({"detail": error_msg})

    user.set_password(password)
    user.save()

    user_password_history_create(user=user, hashed_password=user.password)


def user_password_reset(
    *, id_number: str, birth_date: date, raise_exception: bool = False
):
    user = User.objects.filter(
        Q(student__id_number=id_number, student__birth_date=birth_date)
        | Q(username=id_number, personnel__birth_date=birth_date)
    ).first()

    if not user and raise_exception:
        raise exceptions.NotFound("Unable to process.")

    if user:
        event_publisher.generic(events.USER_PASSWORD_RESET, object=user)


def user_password_reset_confirm(*, uid: str, token: str, password: str):
    try:
        uid = force_str(uid_decoder(uid))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        raise exceptions.ValidationError({"detail": "Invalid data"})

    if not token_generator.check_token(user, token):
        raise exceptions.ValidationError({"detail": "Invalid data"})

    user_password_change(user=user, password=password)


def user_school_group_create(*, school_groups: List[Dict], user: User) -> None:
    user.school_groups.all().delete()
    user.groups.clear()

    for school_group in school_groups:
        school = school_group.get("school")
        roles = school_group.pop("roles")

        user_role_create(roles=roles, user=user)

        user_school_group = UserSchoolGroup.objects.create(school=school, user=user)
        user_school_group.roles.add(*roles)
        user_school_group.save()


@transaction.atomic
def role_create(*, data: Dict) -> Role:
    role_modules = data.pop("role_modules")
    role = Role.admin_objects.create(name=data.get("name"))

    if role_modules:
        role_module_create(role_modules=role_modules, role=role)

    return role


@transaction.atomic
def role_update(*, role: Role, data: Dict) -> Role:
    _data = data.copy()

    role_modules = _data.pop("role_modules", None)

    for field, value in _data.items():
        setattr(role, field, value)

    role.save()

    if role_modules:
        role.permissions.clear()
        role.rolemodule_set.all().delete()
        role_module_create(role_modules=role_modules, role=role)

    return role


def role_module_create(*, role_modules: list[dict], role: Role):
    perm_map = {
        "has_view_perm": "view_permissions",
        "has_add_perm": "add_permissions",
        "has_change_perm": "change_permissions",
        "has_delete_perm": "delete_permissions",
    }

    for role_module in role_modules:
        rm = role.rolemodule_set.create(
            module=role_module.get("module"),
            has_view_perm=role_module.get("has_view_perm", False),
            has_add_perm=role_module.get("has_add_perm", False),
            has_change_perm=role_module.get("has_change_perm", False),
            has_delete_perm=role_module.get("has_delete_perm", False),
        )

        for has_perm, perm_set in perm_map.items():
            if getattr(rm, has_perm, False):
                permissions = getattr(rm.module, perm_set)
                role.permissions.add(*permissions.all())


def role_destroy(*, role: Role) -> bool:
    role.rolemodule_set.all().delete()
    return role.delete()
