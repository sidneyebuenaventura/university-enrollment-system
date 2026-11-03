from django.conf import settings


def prefix_reserved_role_name(name):
    return f"{settings.UNIVERSITY_CORE_RESERVED_ROLE_PREFIX}.{name}"


class ReservedRoleMetaclass(type):
    def __new__(cls, name, bases, attrs):
        klass = super().__new__(cls, name, bases, attrs)
        roles = []

        for key, value in attrs.items():
            if not key.startswith("_"):
                prefixed_name = prefix_reserved_role_name(value)
                setattr(klass, key, prefixed_name)
                roles.append(prefixed_name)

        klass._declared_roles = tuple(roles)
        return klass

    def __iter__(self):
        for role in self._declared_roles:
            yield role


class ReservedRole(metaclass=ReservedRoleMetaclass):
    STUDENT = "student"
    STUDENT_PRE_ENROLLMENT = "student_pre_enrollment"
    STUDENT_ENROLLMENT = "student_enrollment"
    SUPER_ADMIN = "super_admin"


class WebModule:
    DASHBOARD = "web.dashboard"
    USER_ROLES = "web.user_roles"
    USER_ACCOUNTS = "web.user_accounts"
    DRAGONPAY_TRANSACTIONS = "web.dragonpay_transactions"
    SEARCH_FRESHMAN_STUDENTS = "web.freshman_student_search"
    SEARCH_STUDENTS = "web.student_search"


class MobileModule:
    DASHBOARD = "mobile.dashboard"
    PRE_ENROLLMENT = "mobile.pre_enrollment"
    ENROLLMENT = "mobile.enrollment"
    STUDENT_INFORMATION = "mobile.student_information"
    CURRICULUM_CHECKLIST = "mobile.curriculum_checklist"
    STATEMENT_OF_ACCOUNT = "mobile.soa"
