import os
from pathlib import Path

from dotenv import load_dotenv

from celery.schedules import crontab

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "insecure-dev-key-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "users",
    "core",
    "bot",
    "api",
    "anymail",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "absence_bot"),
        "USER": os.getenv("POSTGRES_USER", "absence_bot"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "absence_bot"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 6},
    },
]

# Automatic logout from Django Admin after 10 minutes of inactivity.
SESSION_COOKIE_AGE = 600  # 10 хвилин
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Europe/Warsaw"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
WEBAPP_URL = os.getenv("WEBAPP_URL", "")
WEBAPP_DEV_TELEGRAM_ID = os.getenv("WEBAPP_DEV_TELEGRAM_ID", "")
_WEBAPP_DIST = BASE_DIR / "webapp" / "dist"
STATICFILES_DIRS = [("webapp", _WEBAPP_DIST)] if _WEBAPP_DIST.exists() else []

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = [
    o for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if o
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Telegram bot
# ---------------------------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

CELERY_BEAT_SCHEDULE = {
    "check-and-send-due-broadcasts": {
        "task": "core.tasks.check_and_send_due_broadcasts",
        "schedule": crontab(minute="*/5"),
    },
    "purge-old-sick-leave-files": {
        "task": "core.tasks.purge_old_sick_leave_files",
        "schedule": crontab(hour=3, minute=30),
    },
    "remind-missing-sick-notes": {
        "task": "api.tasks.remind_missing_sick_notes",
        "schedule": crontab(hour=10, minute=0),
    },
}

# Нагадування про неприкріплений лікарняний: через скільки днів після подання,
# з яким інтервалом і скільки разів максимум
SICK_NOTE_REMINDER_AFTER_DAYS = int(os.getenv("SICK_NOTE_REMINDER_AFTER_DAYS", "2"))
SICK_NOTE_REMINDER_INTERVAL_DAYS = int(os.getenv("SICK_NOTE_REMINDER_INTERVAL_DAYS", "2"))
SICK_NOTE_REMINDER_MAX = int(os.getenv("SICK_NOTE_REMINDER_MAX", "3"))

# Скільки днів зберігати файли лікарняних після відправки координатору
SICK_LEAVE_FILE_RETENTION_DAYS = int(os.getenv("SICK_LEAVE_FILE_RETENTION_DAYS", "90"))
# ---------------------------------------------------------------------------
# Email via Resend HTTPS API
# ---------------------------------------------------------------------------
EMAIL_BACKEND = "anymail.backends.resend.EmailBackend"

ANYMAIL = {
    "RESEND_API_KEY": os.getenv("RESEND_API_KEY", ""),
}

DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL",
    "Apolo FreeDays <notifications@apolo.blacky.click>",
)

SITE_BASE_URL = os.getenv("SITE_BASE_URL", "http://localhost:8000")


# ---------------------------------------------------------------------------
# Моніторинг помилок (Sentry). Вмикається лише якщо задано SENTRY_DSN.
# ---------------------------------------------------------------------------
SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
        # Лікарняні — медичні дані: не надсилаємо ні персональних даних, ні тіл запитів
        send_default_pii=False,
        max_request_body_size="never",
        traces_sample_rate=0.0,
    )
    # Railway сам задає назву сервісу — у Sentry видно, де сталася помилка: web, bot чи worker
    sentry_sdk.set_tag("service", os.getenv("RAILWAY_SERVICE_NAME", "local"))

