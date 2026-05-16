"""
Django settings for chopsticks_backend project.
"""

import os
import sys
from pathlib import Path

import dj_database_url
from decouple import config

# Detect test runs (manage.py test, pytest) so we can force a deterministic
# filesystem storage backend regardless of the env-supplied bucket credentials.
RUNNING_TESTS = (
    'test' in sys.argv
    or 'pytest' in sys.argv[0]
    or os.environ.get('PYTEST_CURRENT_TEST') is not None
)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Encoding and locale settings
DEFAULT_CHARSET = 'utf-8'
FILE_CHARSET = 'utf-8'

# Base URL for backend (used for OAuth callbacks, payment webhooks, absolute media URLs).
# Production must set BASE_URL explicitly (e.g. https://api.zmall.ng or *.up.railway.app).
# Empty default is safe for local dev (the helper falls back to relative URLs).
def _normalize_base_url(value: str) -> str:
    value = (value or '').strip().rstrip('/')
    if not value:
        return ''
    if not value.startswith(('http://', 'https://')):
        value = 'https://' + value
    return value


BACKEND_BASE_URL = _normalize_base_url(config('BASE_URL', default=''))

# NOTE: FRONTEND_BASE_URL has been removed for strict multi-tenancy.
# Frontend URLs are now determined from RestaurantSettings.domain via get_frontend_url_from_business().
# Each business must have its domain configured in RestaurantSettings.

# Environment Variables for Production (set these on Railway / host):
# DEBUG=False
# SECRET_KEY=...
# BASE_URL=https://<railway-or-custom-domain>
# ALLOWED_HOSTS=<comma-separated host list>
# CORS_ALLOWED_ORIGINS=<comma-separated origins>
# CSRF_TRUSTED_ORIGINS=<comma-separated origins, including BASE_URL>
# OAUTH_BASE_URL=<defaults to BASE_URL>

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-your-secret-key-here')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='localhost,127.0.0.1',
    cast=lambda v: [s.strip() for s in v.split(',') if s.strip()],
)

# CSRF trusted origins must include the API host (with scheme) once it is known.
# Required for Django admin POSTs behind a TLS-terminating proxy (Railway).
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='',
    cast=lambda v: [s.strip() for s in v.split(',') if s.strip()],
)
if BACKEND_BASE_URL and BACKEND_BASE_URL not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(BACKEND_BASE_URL)

# Application definition
INSTALLED_APPS = [
    'drf_spectacular',
    'unfold',  # Unfold must be before django.contrib.admin
    'unfold.contrib.filters',  # Optional: Advanced filters
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'import_export',
    'drf_yasg',
    
    # Local apps
    'accounts',
    'menu',
    'addresses',
    'orders',
    'loyalty',
    'promotions',
    'core',
    'payments',
    'storefront',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'chopsticks_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'chopsticks_backend.wsgi.application'

# Database
# Production (Railway): set DATABASE_URL (e.g. postgresql://...) and we parse it via dj-database-url.
# Local dev: leave DATABASE_URL unset to fall back to SQLite, matching legacy PythonAnywhere behavior.
_DATABASE_URL = config('DATABASE_URL', default='')
if _DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            _DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=not DEBUG,
        ),
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Custom Authentication Backend
AUTHENTICATION_BACKENDS = [
    'accounts.backends.EmailOrUsernameModelBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images) - WhiteNoise serves these when DEBUG=False
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files
# Production (Railway): S3-compatible bucket via django-storages when BUCKET / AWS_STORAGE_BUCKET_NAME is set.
# Local dev: filesystem under MEDIA_ROOT; Django dev server serves /media/.
USE_S3_STORAGE = bool(
    os.environ.get('BUCKET') or os.environ.get('AWS_STORAGE_BUCKET_NAME')
) and not RUNNING_TESTS

# Optional CDN base URL (Phase 2). When set, absolute_media_url() builds
# stable https://{cdn}/{key} URLs instead of presigning. Leave blank to keep
# Phase 1 presigned URLs against the private bucket.
MEDIA_CDN_BASE_URL = config('MEDIA_CDN_BASE_URL', default='').rstrip('/')

if USE_S3_STORAGE:
    AWS_STORAGE_BUCKET_NAME = os.environ.get('BUCKET') or os.environ['AWS_STORAGE_BUCKET_NAME']
    AWS_S3_ENDPOINT_URL = (
        os.environ.get('ENDPOINT')
        or os.environ.get('AWS_S3_ENDPOINT_URL')
        or 'https://storage.railway.app'
    )
    AWS_S3_REGION_NAME = (
        os.environ.get('REGION')
        or os.environ.get('AWS_S3_REGION_NAME')
        or os.environ.get('AWS_DEFAULT_REGION')
        or 'auto'
    )
    AWS_ACCESS_KEY_ID = os.environ.get('ACCESS_KEY_ID') or os.environ['AWS_ACCESS_KEY_ID']
    AWS_SECRET_ACCESS_KEY = os.environ.get('SECRET_ACCESS_KEY') or os.environ['AWS_SECRET_ACCESS_KEY']
    AWS_S3_ADDRESSING_STYLE = config('AWS_S3_ADDRESSING_STYLE', default='virtual')
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    AWS_DEFAULT_ACL = None
    AWS_S3_FILE_OVERWRITE = False
    AWS_QUERYSTRING_AUTH = config(
        'AWS_QUERYSTRING_AUTH', default=not bool(MEDIA_CDN_BASE_URL), cast=bool
    )
    AWS_QUERYSTRING_EXPIRE = config(
        'AWS_QUERYSTRING_EXPIRE', default=7 * 24 * 3600, cast=int
    )
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'public, max-age=86400',
    }

    STORAGES = {
        'default': {'BACKEND': 'chopsticks_backend.storage_backends.MediaStorage'},
        'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
    }
    # MEDIA_ROOT is unused with S3 storage but Django still expects MEDIA_URL to exist
    # for ImageField string representation; storages overrides url() per request.
    MEDIA_URL = ''
    MEDIA_ROOT = str((BASE_DIR / 'media').resolve())
else:
    MEDIA_URL = '/media/'
    MEDIA_ROOT = str((BASE_DIR / 'media').resolve())
    STORAGES = {
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
    }

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS settings
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:5173,http://127.0.0.1:5173,https://chopsticks-frontend.vercel.app,https://chopsticks-frontend-git-main-khalifas-projects-8b761d27.vercel.app,https://chopsticks-frontend-escfy7lg4-khalifas-projects-8b761d27.vercel.app,https://chopsticksandbowls.com,https://www.chopsticksandbowls.com,https://roschiwater.com,https://www.roschiwater.com,https://zmall.ng,https://www.zmall.ng', cast=lambda v: [s.strip() for s in v.split(',')])

# Additional CORS settings for production
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False  # Keep this False for security
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'ngrok-skip-browser-warning',  # Allow ngrok bypass header
]

# Security settings for production
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    # Railway (and most PaaS) terminate TLS at the edge and forward over HTTP, so we
    # must trust the X-Forwarded-Proto / X-Forwarded-Host headers for request.is_secure()
    # and absolute URL building (e.g. OAuth redirects, Paystack callbacks).
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_X_FORWARDED_HOST = True
    USE_X_FORWARDED_PORT = True

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    # Default for views without a custom class. Catalog uses menu.pagination.MenuItemPageNumberPagination (25, honours ?page_size=).
    'PAGE_SIZE': 25,
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ),
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
    'UNICODE_JSON': True,
}

# JWT settings
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=12),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# Email settings
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@chopsticksandbowls.com')

# Google Maps API
GOOGLE_MAPS_API_KEY = config('GOOGLE_MAPS_API_KEY', default='')

# OAuth base URL - defaults to BACKEND_BASE_URL (can be overridden via OAUTH_BASE_URL env var).
# OAuth credentials are business-specific (stored on RestaurantSettings); this is just the
# host that providers redirect back to. Empty in local dev is fine — providers won't be hit.
OAUTH_BASE_URL = _normalize_base_url(config('OAUTH_BASE_URL', default=BACKEND_BASE_URL))

SOCIAL_AUTH_FACEBOOK_KEY = config('SOCIAL_AUTH_FACEBOOK_KEY', default='')
SOCIAL_AUTH_FACEBOOK_SECRET = config('SOCIAL_AUTH_FACEBOOK_SECRET', default='')

SOCIAL_AUTH_APPLE_ID_CLIENT = config('SOCIAL_AUTH_APPLE_ID_CLIENT', default='')
SOCIAL_AUTH_APPLE_ID_TEAM = config('SOCIAL_AUTH_APPLE_ID_TEAM', default='')
SOCIAL_AUTH_APPLE_ID_KEY = config('SOCIAL_AUTH_APPLE_ID_KEY', default='')

# Restaurant settings - Now handled by RestaurantSettings model
# These variables are no longer used and have been removed for multi-tenancy

# Points system settings
POINTS_PER_DOLLAR = config('POINTS_PER_DOLLAR', default=1, cast=int)
BIRTHDAY_BONUS_POINTS = config('BIRTHDAY_BONUS_POINTS', default=5000, cast=int)
FIRST_ORDER_BONUS_POINTS = config('FIRST_ORDER_BONUS_POINTS', default=1000, cast=int)
REFERRAL_BONUS_POINTS = config('REFERRAL_BONUS_POINTS', default=1000, cast=int)

# QR Code Loyalty Card settings
PHYSICAL_VISIT_POINTS = config('PHYSICAL_VISIT_POINTS', default=500, cast=int)
LUNCH_VISIT_BONUS = config('LUNCH_VISIT_BONUS', default=25, cast=int)
DINNER_VISIT_BONUS = config('DINNER_VISIT_BONUS', default=25, cast=int)
HAPPY_HOUR_BONUS = config('HAPPY_HOUR_BONUS', default=30, cast=int)
MIN_SCAN_INTERVAL_MINUTES = config('MIN_SCAN_INTERVAL_MINUTES', default=30, cast=int)

# Loyalty Tier Sttings
BRONZE_TIER_POINTS = config('BRONZE_TIER_POINTS', default=0, cast=int)
SILVER_TIER_POINTS = config('SILVER_TIER_POINTS', default=50000, cast=int)
GOLD_TIER_POINTS = config('GOLD_TIER_POINTS', default=100000, cast=int)
PLATINUM_TIER_POINTS = config('PLATINUM_TIER_POINTS', default=250000, cast=int)

# Order settings - Defaults for RestaurantSettings model (used when creating new businesses)
# These are defaults only; each business has its own values in RestaurantSettings
DEFAULT_DELIVERY_FEE_BASE = config('DELIVERY_FEE_BASE', default=2000.00, cast=float)
DEFAULT_DELIVERY_FEE_PER_KM = config('DELIVERY_FEE_PER_KM', default=150.00, cast=float)
DEFAULT_TAX_RATE = config('TAX_RATE', default=0.075, cast=float)

# Paystack payment settings
# NOTE: Paystack keys are now business-specific and stored in RestaurantSettings model
# Each business must have its own Paystack keys configured
PAYSTACK_CALLBACK_URL = (BACKEND_BASE_URL.rstrip('/') + '/api/payments/callback/') if BACKEND_BASE_URL else ''
PAYSTACK_BASE_URL = config('PAYSTACK_BASE_URL', default='https://api.paystack.co')

# Django Unfold settings
UNFOLD = {
    "SITE_TITLE": "Chopsticks & Bowls Admin",
    "SITE_HEADER": "Chopsticks & Bowls",
    "SITE_URL": "/",
    "STYLES": [
        lambda request: "/static/css/custom-admin.css",
    ],
    "SCRIPTS": [
        lambda request: "/static/js/custom-admin.js",
    ],
    "COLORS": {
        "primary": {
            "50": "250 245 255",
            "100": "243 232 255",
            "200": "233 213 255",
            "300": "216 180 254",
            "400": "192 132 252",
            "500": "168 85 247",
            "600": "147 51 234",
            "700": "126 34 206",
            "800": "107 33 168",
            "900": "88 28 135",
            "950": "59 7 100",
        },
    },
}

# Roschi Water Unfold settings (for custom admin site)
ROSCHI_UNFOLD = {
    "SITE_TITLE": "Roschi Water Admin",
    "SITE_HEADER": "Roschi Water",
    "SITE_URL": "/roschi-admin/",
    "COLORS": {
        "primary": {
            "50": "240 249 255",  # Water blue shades
            "100": "224 242 254",
            "200": "186 230 253",
            "300": "125 211 252",
            "400": "56 189 248",
            "500": "14 165 233",  # Primary water blue
            "600": "2 132 199",   # Darker blue
            "700": "3 105 161",
            "800": "7 89 133",
            "900": "12 74 110",
            "950": "8 47 73",
        },
    },
}

# Chopsticks & Bowls Unfold settings (for custom admin site)
CHOPSTICKS_UNFOLD = {
    "SITE_TITLE": "Chopsticks & Bowls Admin",
    "SITE_HEADER": "Chopsticks & Bowls",
    "SITE_URL": "/cb-admin/",
    "COLORS": {
        "primary": {
            "50": "250 245 255",  # Purple shades (matching main UNFOLD)
            "100": "243 232 255",
            "200": "233 213 255",
            "300": "216 180 254",
            "400": "192 132 252",
            "500": "168 85 247",
            "600": "147 51 234",
            "700": "126 34 206",
            "800": "107 33 168",
            "900": "88 28 135",
            "950": "59 7 100",
        },
    },
}

# Zmall Unfold settings (clothing & apparel – white primary, black secondary)
ZMALL_UNFOLD = {
    "SITE_TITLE": "Zmall Admin",
    "SITE_HEADER": "Zmall",
    "SITE_URL": "/zmall-admin/",
    "COLORS": {
        "primary": {
            "50": "250 250 250",
            "100": "245 245 245",
            "200": "229 229 229",
            "300": "212 212 212",
            "400": "163 163 163",
            "500": "115 115 115",
            "600": "82 82 82",
            "700": "64 64 64",
            "800": "38 38 38",
            "900": "23 23 23",
            "950": "10 10 10",
        },
    },
}
