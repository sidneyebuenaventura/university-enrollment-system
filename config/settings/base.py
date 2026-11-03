"""
Django settings for the University Enrollment System.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.2/ref/settings/
"""

from datetime import timedelta
from pathlib import Path

import environ
import sentry_sdk
import structlog
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration

from . import openapi as openapi_settings

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Environ
env = environ.Env(
    SECRET_KEY=(str, "devkey"),
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["*"]),
    ENABLE_SILK=(bool, False),
)

env.read_env(BASE_DIR / ".env")

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DEBUG")

ALLOWED_HOSTS = env("ALLOWED_HOSTS")

X_FRAME_OPTIONS = "SAMEORIGIN"

ENABLE_SILK = env("ENABLE_SILK")


# Application definition

DJANGO_ADMIN_APPS = [
    "admin_interface",
    "colorfield",
    "django.contrib.admin",
    "nested_inline",
]

DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework.authtoken",
    "dj_rest_auth",
    "django_extensions",
    "django_js_reverse",
    "django_filters",
    "django_celery_beat",
    "django_object_actions",
    "drf_spectacular",
    "corsheaders",
    "polymorphic",
]

SERVICE_APPS = [
    "university.core",
    "university.core.accounts",
    "university.core.cms",
    "university.core.students",
    "university.core.maintenance",
    "university.payment",
    "university.audit_trail",
    "university.notification",
]


if ENABLE_SILK:
    THIRD_PARTY_APPS += ["silk"]


INSTALLED_APPS = DJANGO_ADMIN_APPS + DJANGO_APPS + THIRD_PARTY_APPS + SERVICE_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_structlog.middlewares.RequestMiddleware",
]


if ENABLE_SILK:
    MIDDLEWARE += ["silk.middleware.SilkyMiddleware"]


SITE_ID = 1

ROOT_URLCONF = "config.urls.core"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "university.framework.context_processors.branding",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    "default": env.db("DATABASE_URL", default=None),
}


# Custom User model
# https://docs.djangoproject.com/en/5.2/topics/auth/customizing/#substituting-a-custom-user-model

AUTH_USER_MODEL = "core_accounts.User"


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Manila"

USE_I18N = True

USE_TZ = True


# Storages
# https://docs.djangoproject.com/en/5.2/ref/settings/#storages
# https://django-storages.readthedocs.io/en/latest/index.html

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

STORAGE_PROVIDER = env("STORAGE_PROVIDER", default="system")


if STORAGE_PROVIDER.lower() == "system":
    MEDIA_URL = "media/"

    MEDIA_ROOT = BASE_DIR / "mediafiles"


if STORAGE_PROVIDER.lower() == "s3":
    STORAGES["default"] = {"BACKEND": "storages.backends.s3boto3.S3Boto3Storage"}

    AWS_S3_ACCESS_KEY_ID = env("AWS_S3_ACCESS_KEY_ID", default=None)

    AWS_S3_SECRET_ACCESS_KEY = env("AWS_S3_SECRET_ACCESS_KEY", default=None)

    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default=None)

    AWS_DEFAULT_ACL = "private"

    AWS_QUERYSTRING_AUTH = False

    MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/"


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = env("STATIC_URL", default="static/")

STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = [
    str(BASE_DIR / "static"),
]

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]


# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Logging
# https://docs.djangoproject.com/en/5.2/topics/logging/#configuring-logging

LOG_LEVEL = "INFO"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json_formatter": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.processors.JSONRenderer(),
        },
        "plain_console": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.dev.ConsoleRenderer(),
        },
        "key_value": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.processors.KeyValueRenderer(
                key_order=["timestamp", "level", "event", "logger"]
            ),
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "plain_console",
        },
        "json_file": {
            "class": "logging.handlers.WatchedFileHandler",
            "filename": "logs/json.log",
            "formatter": "json_formatter",
        },
        "flat_line_file": {
            "class": "logging.handlers.WatchedFileHandler",
            "filename": "logs/flat_line.log",
            "formatter": "key_value",
        },
        "payment_console": {
            "class": "logging.StreamHandler",
            "formatter": "plain_console",
        },
        "payment_json_file": {
            "class": "logging.handlers.WatchedFileHandler",
            "filename": "logs/payment_json.log",
            "formatter": "json_formatter",
        },
        "payment_flat_line_file": {
            "class": "logging.handlers.WatchedFileHandler",
            "filename": "logs/payment_flat_line.log",
            "formatter": "key_value",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
        },
        "django_structlog": {
            "handlers": ["console", "json_file", "flat_line_file"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "university": {
            "handlers": ["console", "json_file", "flat_line_file"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "university.payment": {
            "handlers": [
                "payment_console",
                "payment_json_file",
                "payment_flat_line_file",
            ],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}


# Celery
# http://docs.celeryproject.org/en/latest/userguide/configuration.html

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=None)


# Django REST Framework
# https://www.django-rest-framework.org/

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "university.framework.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}


# dj-rest-auth
# https://dj-rest-auth.readthedocs.io/en/latest/index.html

REST_AUTH = {
    "TOKEN_SERIALIZER": "university.core.accounts.serializers.TokenSerializer",
    "PASSWORD_CHANGE_SERIALIZER": "university.core.accounts.serializers.PasswordChangeSerializer",
    "OLD_PASSWORD_FIELD_ENABLED": True,
    "LOGOUT_ON_PASSWORD_CHANGE": True,
}


# Django JS Reverse
# https://github.com/ierror/django-js-reverse

JS_REVERSE_INCLUDE_ONLY_NAMESPACES = ["university."]


# CORS
# https://github.com/adamchainz/django-cors-headers

CORS_ALLOW_ALL_ORIGINS = True


# Spectacular
# https://drf-spectacular.readthedocs.io/en/latest/

SPECTACULAR_SETTINGS = {
    "TITLE": "University Enrollment System API",
    "VERSION": "0.1",
    "DESCRIPTION": openapi_settings.DESCRIPTION,
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_ADD_EXPLICIT_BLANK_NULL_CHOICE": False,
    "SCHEMA_PATH_PREFIX": "/api",
    "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAdminUser"],
    "AUTHENTICATION_WHITELIST": ["rest_framework.authentication.TokenAuthentication"],
    "EXTENSIONS_INFO": openapi_settings.EXTENSIONS_INFO,
    "EXTENSIONS_ROOT": openapi_settings.EXTENSIONS_ROOT,
    "TAGS": openapi_settings.TAGS,
    "REDOC_DIST": "https://cdn.jsdelivr.net/npm/redoc@2.0.0-rc.70",
}


# Sentry
# https://docs.sentry.io/platforms/python/guides/django/

SENTRY_DSN = env("SENTRY_DSN", default=None)

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=1.0),
        default_integrations=False,
        send_default_pii=True,
        environment=env("SENTRY_ENVIRONMENT", default="development"),
    )


# Hashids

HASHIDS_GRADE_SHEET_SALT = env("HASHIDS_GRADE_SHEET_SALT", default="gradesheet")

HASHIDS_TRAILLOG_SALT = env("HASHIDS_TRAILLOG_SALT", default="traillog")

HASHIDS_PAYMENT_SALT = env("HASHIDS_PAYMENT_SALT", default="payment")

HASHIDS_PAYMENT_SETTLEMENT_SALT = env(
    "HASHIDS_PAYMENT_SETTLEMENT_SALT", default="paymentsettlement"
)

HASHIDS_JOURNAL_VOUCHER_SALT = env(
    "HASHIDS_JOURNAL_VOUCHER_SALT", default="journalvoucher"
)

HASHIDS_MIN_LENGTH = env.int("HASHIDS_MIN_LENGTH", default=6)

HASHIDS_ALPHABET_DEFAULT = env(
    "HASHIDS_ALPHABET_DEFAULT", default="ABCDEFGHJKLMNPRSTUWXYZ1234567890"
)

HASHIDS_ALPHABET_ALPHA_ONLY = env(
    "HASHIDS_ALPHABET_ALPHA_ONLY", default="ABCDEFGHJKLMNPRSTUWXYZ"
)

HASHIDS_GWA_SHEET_SALT = env("HASHIDS_GWA_SHEET_SALT", default="gwasheet")

HASHIDS_STUDENT_REQUEST_SALT = env(
    "HASHIDS_STUDENT_REQUEST_SALT", default="studentrequest"
)


# University Enrollment System

UNIVERSITY_NAME = env("UNIVERSITY_NAME", default="Demo University")

UNIVERSITY_STUDENT_PORTAL_URL = env(
    "UNIVERSITY_STUDENT_PORTAL_URL", default="http://localhost:3001"
)

UNIVERSITY_CORE_RESERVED_ROLE_PREFIX = env("UNIVERSITY_CORE_RESERVED_ROLE_PREFIX", default="system")

UNIVERSITY_PAYMENT_SERVICE = env("UNIVERSITY_PAYMENT_SERVICE", default="http://localhost:8001")

UNIVERSITY_PAYMENT_TRANSACTION_TTL = timedelta(
    minutes=env.int("UNIVERSITY_PAYMENT_TRANSACTION_TTL", default=2880)
)

EMAIL_WHITELIST = env.list("EMAIL_WHITELIST", default=[])

EVENT_BROKER_URL = env("EVENT_BROKER_URL", default=None)

EVENT_GLOBAL_EXCHANGE = env("EVENT_GLOBAL_EXCHANGE", default="university.global")

EVENT_MAP = {
    "notification": {
        "exchange": "direct",
        "queue": "notification",
    },
    "audit_trail": {
        "exchange": "direct",
        "queue": "audit_trail",
    },
}


# Structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

PASSWORD_DURATION = env("PASSWORD_DURATION", default=180)
