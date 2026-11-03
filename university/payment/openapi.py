from drf_spectacular.extensions import OpenApiViewExtension
from drf_spectacular.utils import PolymorphicProxySerializer, extend_schema


class PaymentCreateAPIVewExtension(OpenApiViewExtension):
    target_class = "university.payment.views.PaymentCreateAPIVew"

    def view_replacement(self):
        class TargetClass(self.target_class):
            @extend_schema(
                request=PolymorphicProxySerializer(
                    component_name="PaymentMeta",
                    serializers=self.target_class.serializer_classes_by_payment_method,
                    resource_type_field_name="payment_method",
                ),
                responses=PolymorphicProxySerializer(
                    component_name="PaymentOutputMeta",
                    serializers=self.target_class.output_serializer_classes_by_payment_method,
                    resource_type_field_name="payment_method",
                ),
            )
            def post(self):
                pass

        return TargetClass
