import os
from pathlib import Path
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.getenv("DJANGO_DEBUG", "False") == "True"
# ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "127.0.0.1").split(",")

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
            # "hosts": [("127.0.0.1", 6380)], # Local
            "hosts": [os.environ.get("REDIS_URL")],  # Use Render's Redis URL
        },
    },
}

from .super_secrets import (
    DB_PASSWORD,
    DJ_DATABASE_URL,
    DJANGO_SECRET_KEY,
    gmail_app_password,
    gmail_app_email,
)

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

if DEBUG:
    STATIC_URL = "/static/"
    MEDIA_URL = "/media/"
else:
    STATIC_URL = "https://your-app.onrender.com/static/"
    MEDIA_URL = "https://your-app.onrender.com/media/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

ASGI_APPLICATION = "GotMail.asgi.application"

AUTH_USER_MODEL = "gotmail_service.User"

LOGIN_URL = "login"
LOGOUT_URL = "logout"

STATIC_ROOT = BASE_DIR / "static"

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_ROOT = "user_res"


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
}

CORS_ALLOW_ALL_ORIGINS = True
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CSRF_TRUSTED_ORIGINS = [
        "https://simulated-email-backend.onrender.com",
        "http://127.0.0.1:8000",
        "http://localhost",
        "http://10.0.2.2",
    ]

CSRF_TRUSTED_ORIGINS = [
    "https://simulated-email-backend.onrender.com",
    "http://127.0.0.1:8000",
    "http://localhost",
    "http://10.0.2.2",
    "http://localhost:8000/",
]

CORS_ALLOWED_ORIGINS = [
    "https://simulated-email-backend.onrender.com",
    "http://127.0.0.1:8000",
    "http://localhost",
    "http://10.0.2.2",
]

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "10.0.2.2",
    "simulated-email-backend.onrender.com",
]  # type: ignore

CORS_ALLOW_METHODS = [  # required if making other types of requests besides GET
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
