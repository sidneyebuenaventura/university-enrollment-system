from django.contrib.auth import get_user_model
from django_filters.rest_framework import FilterSet, ModelMultipleChoiceFilter
from rest_framework.filters import BaseFilterBackend

from .models import School
from .selectors import user_schools_get

User = get_user_model()


def _schools(request):
    if request is None:
        return School.objects.none()

    user = request.user

    if user.is_superuser:
        return School.objects.all()

    if user.type == User.Types.ADMIN:
        schools = user_schools_get(user=user)
        school_ids = [school.id for school in schools]
        return School.objects.filter(id__in=school_ids)

    return School.objects.none()


class SchoolFilterSet(FilterSet):
    """Override school_field_name if school field is deeply nested"""

    school = ModelMultipleChoiceFilter(
        queryset=_schools,
        method="filter_school",
        help_text=(
            "School ID. To filter by multiple school ID, add another school key "
            "with a different value. (e.g. ?school=1&school=2)"
        ),
    )
    school_field = "school"

    def filter_school(self, queryset, name, value):
        if not value:
            return queryset
        school_ids = [school.id for school in value]
        return queryset.filter(**{f"{self.school_field}__in": school_ids})


class SchoolFilter(BaseFilterBackend):
    """SchoolFilter should be placed as the first class in filter_backends"""

    def filter_queryset(self, request, queryset, view):
        user = request.user

        if user.is_superuser:
            return queryset

        if user.type == User.Types.ADMIN:
            schools = user_schools_get(user=user)
            school_ids = [school.id for school in schools]
            school_field = getattr(view, "school_field", "school")
            return queryset.filter(**{f"{school_field}__in": school_ids})

        return queryset
