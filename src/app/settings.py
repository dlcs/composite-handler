"""
Django settings for app project.

Generated by 'django-admin startproject' using Django 3.2.9.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""
import os
from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Initialise django-environ and attempt to read environment variables from '.env'.
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("DJANGO_SECRET_KEY", cast=str)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DJANGO_DEBUG", cast=bool, default=True)

ALLOWED_HOSTS = ["*"]

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "app.api.apps.ApiConfig",
    "app.common.apps.CommonConfig",
    "app.engine.apps.EngineConfig",
    "rest_framework",
    "django_q",
    "health_check",
    "health_check.db",
    "health_check.cache",
    "health_check.storage",
    "health_check.contrib.migrations",
    "health_check.contrib.psutil",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "app.urls"

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
            ],
        },
    },
]

WSGI_APPLICATION = "app.wsgi.application"

# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {"default": env.db()}

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR.parent / "dlcs/app_static"

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "loggers": {"": {"level": "INFO", "propagate": True, "handlers": ["console"]}},
}

CACHES = {"default": env.cache()}

Q_CLUSTER = {
    "workers": env("ENGINE_WORKER_COUNT", cast=int, default=2),
    "timeout": env("ENGINE_WORKER_TIMEOUT", cast=int, default=3600),
    "retry": env("ENGINE_WORKER_RETRY", cast=int, default=4500),
    "max_attempts": env("ENGINE_WORKER_MAX_ATTEMPTS", cast=int, default=0),
}

if sqs_queue_name := env.str("SQS_BROKER_QUEUE_NAME", default=""):
    Q_CLUSTER["name"] = sqs_queue_name
    Q_CLUSTER["sqs"] = {}
else:
    Q_CLUSTER["orm"] = "default"

SCRATCH_DIRECTORY = env.path("SCRATCH_DIRECTORY", default="/tmp/scratch")

WEB_SERVER = {
    "scheme": env("WEB_SERVER_SCHEME", cast=str, default="http"),
    "hostname": env("WEB_SERVER_HOSTNAME", cast=str, default="localhost:8000"),
}

PDF_RASTERIZER = {
    "thread_count": env("PDF_RASTERIZER_THREAD_COUNT", cast=int, default=3),
    "format": env("PDF_RASTERIZER_FORMAT", cast=str, default="jpg"),
    "dpi": env("PDF_RASTERIZER_DPI", cast=int, default=500),
    "fallback_dpi": env("PDF_RASTERIZER_FALLBACK_DPI", cast=int, default=200),
    "max_length": env("PDF_RASTERIZER_MAX_LENGTH", cast=int, default=0),
}

ORIGIN_CONFIG = {"chunk_size": env("ORIGIN_CHUNK_SIZE", cast=int, default=8192)}

DLCS = {
    "api_root": env.url("DLCS_API_ROOT", default="https://api.dlcs.digirati.io/"),
    "s3_bucket_name": env(
        "DLCS_S3_BUCKET_NAME", cast=str, default="dlcs-composite-images"
    ),
    "s3_object_key_prefix": env(
        "DLCS_S3_OBJECT_KEY_PREFIX", cast=str, default="composites"
    ),
    "s3_upload_threads": env("DLCS_S3_UPLOAD_THREADS", cast=int, default=8),
    "batch_size": env("DLCS_BATCH_SIZE", cast=int, default=100),
}
