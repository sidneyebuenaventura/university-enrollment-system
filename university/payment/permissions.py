from rest_framework.permissions import BasePermission


class IsBukasWebhook(BasePermission):
    """No permission checks yet. Currently used as a tag for documentation."""

    badge = "![BukasWebhook](https://img.shields.io/badge/Webhook-Bukas-black)"

    def has_permission(self, request, view):
        return True


class IsDragonpayWebhook(BasePermission):
    """No permission checks yet. Currently used as a tag for documentation."""

    badge = "![DragonpayWebhook](https://img.shields.io/badge/Webhook-Dragonpay-black)"

    def has_permission(self, request, view):
        return True
