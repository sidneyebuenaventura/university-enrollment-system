from drf_spectacular.extensions import OpenApiSerializerExtension, OpenApiViewExtension
from drf_spectacular.utils import (
    PolymorphicProxySerializer,
    extend_schema,
    extend_schema_field,
    extend_schema_serializer,
    extend_schema_view,
)
from rest_framework.permissions import IsAuthenticated

from university.framework.permissions import IsAdminUser, IsStudentUser


class StudentUserDetailsSerializerExtension(OpenApiSerializerExtension):
    target_class = "university.core.accounts.serializers.StudentUserDetailsSerializer"

    def map_serializer(self, auto_schema, direction):
        from university.core.accounts.serializers import ModuleSerializer
        from university.core.students.serializers import StudentRetrieveSerializer

        class TargetClass(self.target_class):
            @extend_schema_field(StudentRetrieveSerializer)
            def get_student(self):
                pass

        return auto_schema._map_serializer(TargetClass, direction)


class WebLoginViewExtension(OpenApiViewExtension):
    target_class = "university.core.accounts.views.WebLoginView"

    def view_replacement(self):
        from university.core.accounts.serializers import TokenSerializer, UserDetailsSerializer

        @extend_schema_serializer()
        class WebTokenSerializer(TokenSerializer):
            def get_user(obj) -> UserDetailsSerializer:
                return super().get_user()

        @extend_schema_view(post=extend_schema(auth=[], responses=WebTokenSerializer))
        class Decorated(self.target_class):
            permission_classes = [IsAdminUser]

        return Decorated


class MobileLoginViewExtension(OpenApiViewExtension):
    target_class = "university.core.accounts.views.MobileLoginView"

    def view_replacement(self):
        from university.core.accounts.serializers import (
            StudentUserDetailsSerializer,
            TokenSerializer,
        )

        @extend_schema_serializer()
        class MobileTokenSerializer(TokenSerializer):
            def get_user(obj) -> StudentUserDetailsSerializer:
                return super().get_user()

        @extend_schema_view(
            post=extend_schema(auth=[], responses=MobileTokenSerializer)
        )
        class Decorated(self.target_class):
            permission_classes = [IsStudentUser]

        return Decorated


class LogoutViewExtension(OpenApiViewExtension):
    target_class = "university.core.accounts.views.LogoutView"

    def view_replacement(self):
        @extend_schema_view(get=extend_schema(exclude=True))
        class Decorated(self.target_class):
            permission_classes = [IsAuthenticated]

        return Decorated


class UserDetailsViewExtension(OpenApiViewExtension):
    target_class = "university.core.accounts.views.UserDetailsView"

    def view_replacement(self):
        from university.core.accounts.serializers import (
            StudentUserDetailsSerializer,
            UserDetailsSerializer,
        )

        # Temporary alias. Remove when name is fixed in serializers.py
        class AdminUserDetailsSerializer(UserDetailsSerializer):
            pass

        class Decorated(self.target_class):
            @extend_schema(
                responses=PolymorphicProxySerializer(
                    component_name="MetaUser",
                    serializers=[
                        AdminUserDetailsSerializer,
                        StudentUserDetailsSerializer,
                    ],
                    resource_type_field_name=None,
                )
            )
            def get(self):
                """User Retrieve

                Retrieves user data of authenticated User.
                """

            @extend_schema(
                exclude=True
            )  # Disable for now as we do not know how it handles updates based on user type.
            def put(self):
                """User Update

                Updates data of authenticated User.
                """

            @extend_schema(
                exclude=True
            )  # Disable for now as we do not know how it handles updates based on user type.
            def patch(self):
                """User Partial Update

                Updates data of authenticated User.
                """

        return Decorated


class StudentEnrollmentLatestAPIViewExtension(OpenApiViewExtension):
    target_class = "university.core.students.views.StudentEnrollmentLatestAPIView"

    def view_replacement(self):
        polymorphic_serializer = PolymorphicProxySerializer(
            component_name="EnrollmentMeta",
            serializers=self.target_class.serializer_classes_by_step,
            resource_type_field_name="step",
        )

        class TargetClass(self.target_class):
            @extend_schema(tags=["student-enrollment"])
            def get(self):
                pass

            @extend_schema(
                request=polymorphic_serializer,
                responses=polymorphic_serializer,
                tags=["student-enrollment"],
            )
            def patch(self):
                """Student Enrollment Partial Update

                Editable fields are based on the provided "step" field.

                During "Pre-Enrollment" Status, Steps 1, 2, and 3 are allowed.
                Editing previous steps are also allowed.

                During "Enrollment" Status, only Step 4 is allowed.
                Step 4 can only be updated once.

                For all scenarios not stated above, all steps are locked for updates.
                """

        return TargetClass


class StudentEnrollmentRetrieveUpdateAPIViewExtension(
    StudentEnrollmentLatestAPIViewExtension
):
    target_class = "university.core.students.views.StudentEnrollmentRetrieveUpdateAPIView"


class FacultyDetailSerializerExtension(OpenApiSerializerExtension):
    target_class = "university.core.accounts.serializers.FacultyDetailSerializer"

    def map_serializer(self, auto_schema, direction):
        from university.core.cms.serializers import ClassSerializer

        class TargetClass(self.target_class):
            @extend_schema_field(ClassSerializer)
            def get_subject_classes(self):
                pass

        return auto_schema._map_serializer(TargetClass, direction)
