from django.urls import resolve
from drf_spectacular.openapi import AutoSchema as SpectacularAutoSchema
from drf_spectacular.plumbing import get_doc
from rest_framework.permissions import IsAuthenticated, OperandHolder

from .permissions import IsAdminUser, IsNewAdminUser, IsNewStudentUser, IsStudentUser
from .serializers import InlineSerializerMixin

PERMISSION_BADGES = {
    IsAdminUser: "![AdminUser](https://img.shields.io/badge/User-Admin-red)",
    IsNewAdminUser: "![AdminUser](https://img.shields.io/badge/User-New_Admin-red)",
    IsStudentUser: "![StudentUser](https://img.shields.io/badge/User-Student-brightgreen)",
    IsNewStudentUser: "![NewStudentUser](https://img.shields.io/badge/User-New_Student-brightgreen)",
}
USER_PERMISSIONS = [IsAdminUser, IsStudentUser]


class AutoSchema(SpectacularAutoSchema):
    def get_description(self):
        description = ""
        badges = self.get_permission_badges()

        if badges:
            description = f"{description}{' '.join(badges)}\n\n"

        path_name = resolve(self.path).view_name
        path_doc = f"Path Name: `{path_name}`"
        description = f"{description}{path_doc}\n\n"

        view_description = super().get_description()
        return f"{description}\n\n{view_description}"

    def get_summary(self):
        summary = self.get_summary_from_attr()
        if summary:
            return summary

        docstring = self.get_docstring()
        summary, _ = self.split_summary_from_docstring(docstring)
        if summary:
            return summary

        operation_id = self.get_operation_id()
        summary = [word.title() for word in operation_id.split("_")]
        return " ".join(summary)

    def get_docstring(self):
        action_or_method = getattr(
            self.view, getattr(self.view, "action", self.method.lower()), None
        )
        view_doc = get_doc(self.view.__class__)
        action_doc = get_doc(action_or_method)
        return action_doc or view_doc

    def get_summary_from_attr(self):
        summaries = getattr(self.view, "summaries", {})
        summary = summaries.get(getattr(self.view, "action", self.method.lower()))
        if summary:
            return summary

    def split_summary_from_docstring(self, docstring):
        # OpenAPI 3.0 spec doesn't specify max length but 2.0 says summary
        # should be under 120 characters
        summary_max_len = 120
        summary = None
        description = docstring

        # https://www.python.org/dev/peps/pep-0257/#multi-line-docstrings
        sections = docstring.split("\n\n", 1)

        if len(sections) == 1:
            summary = docstring.strip()
            description = None

        if len(sections) == 2:
            sections[0] = sections[0].strip()

            if len(sections[0]) < summary_max_len:
                summary, description = sections
                description = description.strip()

        return summary, description

    def get_permission_badge(self, perm):
        badge_override = PERMISSION_BADGES.get(perm)
        badge = getattr(perm, "badge", None) or badge_override
        return badge

    def get_permission_badges(self):
        perms = [p.__class__ for p in self.view.get_permissions()]
        badges = []

        if len(perms) == 1 and perms[0] == IsAuthenticated:
            # Any type of user is allowed as long as they're authenticated
            return [
                PERMISSION_BADGES[perm]
                for perm in USER_PERMISSIONS
                if perm in PERMISSION_BADGES
            ]

        for perm in perms:
            if isinstance(perm, OperandHolder):
                perm1 = perm.op1_class()
                perm2 = perm.op2_class()
                badge1 = self.get_permission_badge(perm1)
                badge2 = self.get_permission_badge(perm2)
                badges += [badge1, badge2]
                continue

            badge = self.get_permission_badge(perm)
            if badge:
                badges.append(badge)

        return badges

    def get_request_serializer(self):
        view = self.view
        view_name = type(view).__name__

        if hasattr(view, "InputSerializer"):
            serializer_class = getattr(view, "InputSerializer")
            return type(f"{view_name}InputSerializer", (serializer_class,), {})
        elif InlineSerializerMixin in view.__class__.__bases__:
            serializer = super().get_request_serializer()
            return type(f"{view_name}InputSerializer", (serializer.__class__,), {})

        return super().get_request_serializer()

    def get_response_serializers(self):
        view = self.view
        view_name = type(view).__name__

        if hasattr(view, "OutputSerializer"):
            serializer_class = getattr(view, "OutputSerializer")
            return type(f"{view_name}OutputSerializer", (serializer_class,), {})
        elif InlineSerializerMixin in view.__class__.__bases__:
            serializer = super().get_response_serializers()
            return type(f"{view_name}OutputSerializer", (serializer.__class__,), {})

        return super().get_response_serializers()
