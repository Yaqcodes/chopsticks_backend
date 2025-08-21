"""
Django settings for chopsticks_backend project.
"""

import os
from pathlib import Path
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Encoding and locale settings
DEFAULT_CHARSET = 'utf-8'
FILE_CHARSET = 'utf-8'
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Base URL for frontend
BASE_URL = config('BASE_URL', default='http://localhost:5173')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-your-secret-key-here')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=lambda v: [s.strip() for s in v.split(',')])

# Application definition
INSTALLED_APPS = [
    'unfold',  # Must come before django.contrib.admin
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
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
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
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
TIME_ZONE = "Africa/Lagos"

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
# STATIC_ROOT = os.path.join(BASE_DIR, 'static')
# If you have a top-level "static" folder at the same level as manage.py:
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS settings
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:5173,http://127.0.0.1:5173', cast=lambda v: [s.strip() for s in v.split(',')])
CORS_ALLOW_CREDENTIALS = True

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
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

# Social Authentication settings
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = config('SOCIAL_AUTH_GOOGLE_OAUTH2_KEY', default='')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = config('SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET', default='')

SOCIAL_AUTH_FACEBOOK_KEY = config('SOCIAL_AUTH_FACEBOOK_KEY', default='')
SOCIAL_AUTH_FACEBOOK_SECRET = config('SOCIAL_AUTH_FACEBOOK_SECRET', default='')

SOCIAL_AUTH_APPLE_ID_CLIENT = config('SOCIAL_AUTH_APPLE_ID_CLIENT', default='')
SOCIAL_AUTH_APPLE_ID_TEAM = config('SOCIAL_AUTH_APPLE_ID_TEAM', default='')
SOCIAL_AUTH_APPLE_ID_KEY = config('SOCIAL_AUTH_APPLE_ID_KEY', default='')

# Restaurant settings
RESTAURANT_NAME = config('RESTAURANT_NAME', default='Chopsticks and Bowls')
RESTAURANT_ADDRESS = config('RESTAURANT_ADDRESS', default='')
RESTAURANT_PHONE = config('RESTAURANT_PHONE', default='')
RESTAURANT_EMAIL = config('RESTAURANT_EMAIL', default='')

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

# Order settings - Now handled by RestaurantSettings model
MINIMUM_ORDER_AMOUNT=config('MINIMUM_ORDER_AMOUNT', default=1000.00, cast=float)
DEFAULT_DELIVERY_FEE_BASE=config('DELIVERY_FEE_BASE', default=2000.00, cast=float)
DEFAULT_DELIVERY_FEE_PER_KM=config('DELIVERY_FEE_PER_KM', default=150.00, cast=float)
DEFAULT_TAX_RATE=config('TAX_RATE', default=0.075, cast=float)

# Paystack payment settings
PAYSTACK_SECRET_KEY = config('PAYSTACK_SECRET_KEY_TEST', default='')
PAYSTACK_PUBLIC_KEY = config('PAYSTACK_PUBLIC_KEY_TEST', default='')
PAYSTACK_CALLBACK_URL = BASE_URL + '/payment/callback'
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
}
