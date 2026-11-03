from django.conf import settings


def branding(request):
    """Expose institution branding to server-rendered templates."""
    return {
        "UNIVERSITY_NAME": settings.UNIVERSITY_NAME,
        "STUDENT_PORTAL_URL": settings.UNIVERSITY_STUDENT_PORTAL_URL,
    }
