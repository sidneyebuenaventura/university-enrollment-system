from django.conf import settings


def branding(request):
    return {
        "UNIVERSITY_NAME": settings.UNIVERSITY_NAME,
        "STUDENT_PORTAL_URL": settings.UNIVERSITY_STUDENT_PORTAL_URL,
    }
