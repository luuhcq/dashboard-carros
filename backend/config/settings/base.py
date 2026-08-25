"""
Configurações compartilhadas por todos os ambientes.
Nada de segredo ou valor específico de ambiente aqui — tudo vem do .env.
"""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = BASE_DIR.parent

env = environ.Env()
# .env fica na raiz do monorepo (mesmo arquivo usado pelo docker-compose),
# não duplicado dentro de backend/.
environ.Env.read_env(REPO_ROOT / '.env')

SECRET_KEY = env('SECRET_KEY')

DEBUG = env.bool('DEBUG', default=False)

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    'storages',

    # Local
    'authentication',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('POSTGRES_DB'),
        'USER': env('POSTGRES_USER'),
        'PASSWORD': env('POSTGRES_PASSWORD'),
        'HOST': env('POSTGRES_HOST', default='localhost'),
        'PORT': env('POSTGRES_PORT', default='5432'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/6.1/topics/i18n/

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.1/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'


# Media / storage
# Backend trocável via STORAGE_BACKEND: 'local' (dev) ou 's3' (S3-compatible,
# ex.: AWS S3, MinIO, DigitalOcean Spaces) — troca de ambiente sem alterar código.

MEDIA_URL = 'media/'
STORAGE_BACKEND = env('STORAGE_BACKEND', default='local')

if STORAGE_BACKEND == 's3':
    STORAGES = {
        'default': {
            'BACKEND': 'storages.backends.s3.S3Storage',
        },
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    }
    AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID', default=None)
    AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY', default=None)
    AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME', default=None)
    AWS_S3_ENDPOINT_URL = env('AWS_S3_ENDPOINT_URL', default=None)
    AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME', default=None)
    AWS_DEFAULT_ACL = env('AWS_DEFAULT_ACL', default=None)
else:
    STORAGES = {
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    }
    MEDIA_ROOT = BASE_DIR / 'media'


# CORS
# https://github.com/adamchainz/django-cors-headers

CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])


# Django REST Framework

REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'authentication.authentication.CookieJWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Dashboard Revenda API',
    'DESCRIPTION': 'API do Dashboard de gestão e visualização de dados de revenda de carros.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}


# JWT (djangorestframework-simplejwt)
# Tokens trafegam só via cookie httpOnly, nunca no corpo da resposta JSON.
# JWT_AUTH_COOKIE_SECURE é definido explicitamente em cada settings de ambiente
# (dev.py / prod.py), nunca aqui — mesmo motivo do DEBUG/ALLOWED_HOSTS.

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
}

JWT_AUTH_COOKIE = 'access_token'
JWT_AUTH_REFRESH_COOKIE = 'refresh_token'
JWT_AUTH_COOKIE_SAMESITE = 'Lax'


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
