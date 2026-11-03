from datetime import date

from django.contrib.auth.hashers import check_password

from .models import (
    AcademicYear,
    Module,
    PasswordHistory,
    Personnel,
    RoleModule,
    School,
    Semester,
    User,
    UserSchoolGroup,
)


def _role_module_flatten(*, role_module: RoleModule) -> dict:
    return {
        "name": role_module.module.name,
        "description": role_module.module.description,
        "codename": role_module.module.codename,
        "has_view_perm": role_module.has_view_perm,
        "has_add_perm": role_module.has_add_perm,
        "has_change_perm": role_module.has_change_perm,
        "has_delete_perm": role_module.has_delete_perm,
    }


def _role_modules_normalize(*, role_modules: list[RoleModule]) -> list:
    role_module_map = {}
    perm_flags = ["has_view_perm", "has_add_perm", "has_change_perm", "has_delete_perm"]

    for role_module in role_modules:
        key = role_module.module.codename
        data = _role_module_flatten(role_module=role_module)

        if key not in role_module_map:
            role_module_map[key] = data
            continue

        for perm_flag in perm_flags:
            if data[perm_flag]:
                role_module_map[key][perm_flag] = True

    return list(role_module_map.values())


def user_modules_get(*, user: User) -> list[Module]:
    modules = Module.objects.none()

    if user.is_superuser:
        modules = Module.objects.filter(platform=Module.Platforms.WEB)
    else:
        for role in user.groups.all():
            modules = modules.union(role.modules.all())

    return modules.order_by("order")


def user_role_modules_get(*, user: User) -> list[RoleModule]:
    role_modules = RoleModule.objects.none()

    if user.is_superuser:
        role_modules = RoleModule.objects.filter(module__platform=Module.Platforms.WEB)
    else:
        for role in user.groups.all():
            role_modules = role_modules.union(role.rolemodule_set.all())

    return role_modules


def user_role_modules_data_get(*, user: User) -> list:
    role_modules = user_role_modules_get(user=user)
    return _role_modules_normalize(role_modules=role_modules)


def user_school_role_modules_get(*, user: User, school: School) -> list[RoleModule]:
    role_modules = RoleModule.objects.none()

    if user.is_superuser:
        role_modules = RoleModule.objects.filter(module__platform=Module.Platforms.WEB)
    else:
        user_school_groups = user.school_groups.filter(school=school)
        for user_school_group in user_school_groups:
            for role in user_school_group.roles.all():
                role_modules = role_modules.union(role.rolemodule_set.all())

    return role_modules


def user_schools_get(*, user: User) -> list[School]:
    if user.is_superuser:
        return School.objects.all()
    return [school_group.school for school_group in user.school_groups.all()]


def user_password_history_get(*, user: User, password: str, limit: int = 2):
    password_histories = user.password_histories.filter(
        type=PasswordHistory.Types.CHANGED
    ).order_by("-created_at")[:limit]

    for password_history in password_histories:
        if check_password(password, password_history.value):
            return password_history


def school_group_role_modules_data_get(*, school_group: UserSchoolGroup) -> list:
    role_modules = user_school_role_modules_get(
        user=school_group.user, school=school_group.school
    )
    return _role_modules_normalize(role_modules=role_modules)


def faculty_list_get() -> list[Personnel]:
    return Personnel.active_objects.filter(
        category__in=[
            Personnel.Categories.CONTRACTUAL_FACULTY,
            Personnel.Categories.FACULTY,
            Personnel.Categories.VISITING_LECTURER,
        ]
    )


def faculty_current_schedule_list_get(faculty: Personnel):
    current_academic_year = current_academic_year_get()
    current_semester = current_semester_get()

    if current_academic_year and current_semester:
        return faculty.subject_classes.filter(semester=current_semester)
    else:
        return None


def current_academic_year_get() -> AcademicYear:
    academic_years = AcademicYear.objects.filter(year_start__gte=date.today().year - 1)

    for year in academic_years:
        if year.date_start and year.date_end:
            if year.date_start <= date.today() <= year.date_end:
                return year

            next_school_year = AcademicYear.objects.filter(
                year_start=year.year_start + 1
            ).first()

            if next_school_year and next_school_year.date_start > year.date_end:
                return year
    else:
        return None


def current_semester_get() -> Semester:
    current_academic_year = current_academic_year_get()

    if current_academic_year:
        for semester in current_academic_year.semesters.all():
            if semester.date_start and semester.date_end:
                if semester.date_start <= date.today() <= semester.date_end:
                    return semester

                next_semester = current_academic_year.semesters.filter(
                    order=semester.order + 1
                ).first()

                if not next_semester:
                    return semester

                if next_semester and next_semester.date_start > date.today():
                    return semester

    return None


def next_semester_get() -> Semester:
    current_sem = current_semester_get()
    if current_sem:
        current_academic_year = current_sem.academic_year
        next_semester = current_academic_year.semesters.filter(
            order=current_sem.order + 1
        ).first()

        if not next_semester:
            next_academic_year = AcademicYear.objects.filter(
                year_start=current_academic_year.year_start + 1
            ).first()
            next_semester = next_academic_year.semesters.order_by("order").first()

        return next_semester
    return None


def previous_semester_get() -> Semester:
    current_sem = current_semester_get()
    if current_sem:
        current_academic_year = current_sem.academic_year
        previous_semester = current_academic_year.semesters.filter(
            order=current_sem.order - 1
        ).first()

        if not previous_semester:
            previous_academic_year = AcademicYear.objects.filter(
                year_start=current_academic_year.year_start - 1
            ).first()
            previous_semester = previous_academic_year.semesters.order_by(
                "-order"
            ).first()

        return previous_semester
    return False


def _user_module_flatten(*, module: Module) -> dict:
    return {
        "name": module.name,
        "description": module.description,
        "codename": module.codename,
        "has_view_perm": module.view_permissions.count() > 0,
        "has_add_perm": module.add_permissions.count() > 0,
        "has_change_perm": module.change_permissions.count() > 0,
        "has_delete_perm": module.delete_permissions.count() > 0,
    }


def user_modules_join(*, user: User, role_modules: list) -> list:
    user_modules = []

    for module in user.modules.all():
        module_dict = _user_module_flatten(module=module)
        user_modules.append(module_dict)

    return user_modules + role_modules
