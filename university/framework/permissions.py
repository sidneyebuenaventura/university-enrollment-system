from django.core.exceptions import ObjectDoesNotExist
from rest_framework.permissions import BasePermission
from rest_framework.permissions import IsAdminUser as DefaultIsAdminUser


class IsSuperUser(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_superuser
            and request.user.get_password_rem_days() > 0
        )


class IsSuperUserNPC(BasePermission):
    """No Valid Password Checking"""

    def has_permission(self, request, view):
        return request.user and request.user.is_superuser


class IsAdminUser(DefaultIsAdminUser):
    def has_permission(self, request, view):
        is_admin = super().has_permission(request, view)
        return (
            is_admin
            and not request.user.is_first_login
            and request.user.get_password_rem_days() > 0
        )


class IsAdminUserNPC(DefaultIsAdminUser):
    """No Valid Password Checking"""

    def has_permission(self, request, view):
        is_admin = super().has_permission(request, view)
        return is_admin and not request.user.is_first_login


class IsNewAdminUser(DefaultIsAdminUser):
    def has_permission(self, request, view):
        is_admin = super().has_permission(request, view)
        return is_admin and request.user.is_first_login


class IsNewStudentUser(BasePermission):
    """
    Allows access only to newly generated student users.
    """

    def has_permission(self, request, view):
        if not request.user:
            return False

        try:
            request.user.student
        except ObjectDoesNotExist:
            return False

        if not request.user.is_first_login:
            return False

        return True


class IsStudentUser(BasePermission):
    """
    Allows access only to student users.
    """

    def has_permission(self, request, view):
        if not request.user:
            return False

        try:
            request.user.student
        except ObjectDoesNotExist:
            return False

        if request.user.is_first_login or request.user.get_password_rem_days() <= 0:
            return False

        return True


class IsStudentUserNPC(BasePermission):
    """
    Allows access only to student users.
    No Valid Password Checking
    """

    def has_permission(self, request, view):
        if not request.user:
            return False

        try:
            request.user.student
        except ObjectDoesNotExist:
            return False

        if request.user.is_first_login:
            return False

        return True
