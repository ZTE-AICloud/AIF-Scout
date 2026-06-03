# Copyright 2025 ZTE Corporation.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from pathlib import Path
import datetime
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Logging
LOG_DIR = os.path.join(BASE_DIR, "pv/logs/")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

def get_secret_key(file_path):
    try:
        with open(file_path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        raise RuntimeError("SECRET_KEY not found")
    except PermissionError:
        raise RuntimeError("SECRET_KEY has no permission")


SECRET_KEY = get_secret_key(os.path.expanduser("~/secret"))

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

LOG_LEVEL = "DEBUG" if DEBUG else "INFO"
ERROR_LEVEL = "DEBUG" if DEBUG else "ERROR"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s"
        },
        "simple": {"format": "%(levelname)s %(message)s"},
        "django.server": {
            "()": "django.utils.log.ServerFormatter",
            "format": "[{server_time}] {message}",
            "style": "{",
        },
    },
    "handlers": {
        "file": {
            "level": LOG_LEVEL,
            "class": "logging.FileHandler",
            "filename": os.path.join(LOG_DIR, "azalea.log"),
            "formatter": "verbose",
        },
        "console": {
            "level": LOG_LEVEL,
            "filters": ["require_debug_true"],
            "class": "logging.StreamHandler",
        },
        "django.server": {
            "level": LOG_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": "django.server",
        },
    },
    "loggers": {
        "": {
            "handlers": ["file"],
            "level": LOG_LEVEL,
            "propagate": True,
        },
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.server": {
            "handlers": ["file"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "pssh": {
            "handlers": ["file"],
            "level": ERROR_LEVEL,
            "propagate": False,
        }
    },
}

MEDIA_ROOT = os.path.join(BASE_DIR, "pv/upload/")

FILE_UPLOAD_TEMP_DIR = os.path.join(BASE_DIR, "pv/upload_tmp/")

FILE_UPLOAD_HANDLERS = [
    "django.core.files.uploadhandler.TemporaryFileUploadHandler",
]


# Use secure cookie
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_AGE = None
SESSION_COOKIE_AGE = 60 * 60 * 72
SESSION_COOKIE_NAME = "azalea_sessionid"
CSRF_COOKIE_NAME = "azalea_csrftoken"

APPEND_SLASH = False

ALLOWED_HOSTS = ["0.0.0.0", "127.0.0.1"]


CSRF_TRUSTED_ORIGINS = [
    "https://0.0.0.0:8001",
    "https://0.0.0.0:9001",
    "https://127.0.0.1:8001",
    "https://127.0.0.1:9001",
]


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "axes",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "channels",
    "inspector",
]


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTStatelessUserAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',   # 匿名用户
        'rest_framework.throttling.UserRateThrottle',   # 认证用户
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '200/hour',   # 匿名用户每小时200次
        'user': '2000/hour'   # 认证用户每小时2000次
    }
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": datetime.timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": datetime.timedelta(days=1),
}


CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}

if DEBUG:
    INSTALLED_APPS.insert(0, "daphne")
    CHANNEL_LAYERS["default"] = {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
        "CONFIG": {"capacity": 100},
    }


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "azalea.urls"

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


WSGI_APPLICATION = "azalea.wsgi.application"
ASGI_APPLICATION = "azalea.asgi.application"


AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db/db.sqlite3'),
        'OPTIONS': {
            'timeout': 20,
        }
    }
}

AUTH_USER_MODEL = "inspector.CustomUser"


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

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

AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = datetime.timedelta(minutes=5)
AXES_LOCK_OUT_AT_FAILURE = True
AXES_ENABLE_ACCESS_FAILURE_LOG = True

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Shanghai"

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
