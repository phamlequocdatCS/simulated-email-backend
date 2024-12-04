import os
from pathlib import Path

import dj_database_url
from google.oauth2 import service_account

from .super_secrets import (
    DJ_DATABASE_URL,
    DJANGO_SECRET_KEY,
    gmail_app_email,
    gmail_app_password,
)

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.getenv("DJANGO_DEBUG", "False") == "True"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "127.0.0.1").split(",")

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "daphne",
    "django.contrib.staticfiles",
    "corsheaders",
    "gotmail_service",
    "channels",
    "rest_framework",
    "storages",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
]

ROOT_URLCONF = "GotMail.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "GotMail.wsgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [
                os.environ.get("REDIS_URL"),
            ],
        },
    },
}


DATABASES = {
    "default": dj_database_url.config(default=DJ_DATABASE_URL, conn_max_age=600)
}

SECRET_KEY = DJANGO_SECRET_KEY

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

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

ASGI_APPLICATION = "GotMail.asgi.application"

AUTH_USER_MODEL = "gotmail_service.User"

LOGIN_URL = "login"
LOGOUT_URL = "logout"

STATIC_ROOT = BASE_DIR / "static"
STATIC_URL = "/static/"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


# Google Cloud Storage configuration for MEDIA
DEFAULT_FILE_STORAGE = "storages.backends.gcloud.GoogleCloudStorage"
GS_BUCKET_NAME = os.environ.get("GCLOUD_BUCKET")
GS_LOCATION = "media"  # Optional: store media files in a specific folder
MEDIA_URL = f"https://storage.googleapis.com/{GS_BUCKET_NAME}/media/"
GS_QUERYSTRING_AUTH = False
GS_DEFAULT_ACL = None # type: ignore

# Optional: Load credentials from an environment variable or Render's Secret File

GS_CREDENTIALS = service_account.Credentials.from_service_account_file(
    os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "/etc/secrets/gcs-key.json")
)


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
}


CSRF_TRUSTED_ORIGINS = [
    "https://simulated-email-backend.onrender.com",
    "https://phamlequocdatcs.github.io",
]

CORS_ALLOWED_ORIGINS = [
    "https://simulated-email-backend.onrender.com",
    "https://phamlequocdatcs.github.io",
]

ALLOWED_HOSTS = ["simulated-email-backend.onrender.com", "phamlequocdatcs.github.io"]

# required if making other types of requests besides GET
CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

CORS_ALLOW_HEADERS = [
    "content-type",
    "x-csrftoken",
    "access-control-allow-origin",
    "authorization",
]

CORS_ALLOW_CREDENTIALS = True  # Important if you're using cookies or authentication that relies on credentials

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = gmail_app_email
EMAIL_HOST_PASSWORD = gmail_app_password
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": "/tmp/debug.log",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["file"],
            "level": "DEBUG",
            "propagate": True,
        },
    },
}
