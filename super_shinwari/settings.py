from pathlib import Path
from decimal import Decimal
import os
import dj_database_url   # deployment k liye

# ---------- Base Directory ----------
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------- Security ----------
# NOTE: Development ke liye theek hai; production me env se load karna.
SECRET_KEY = 'django-insecure-riwe#29@ej(vuhn!=91@a3rup57zsj1ye+m(=_rk9%4z@)5(fo'

# Development me True rakho, deployment (production) me False karo
DEBUG = True

# Dev ke liye '*', prod me apna domain/host dalna
ALLOWED_HOSTS = ['*']

# ---------- Installed Apps ----------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'widget_tweaks',

    # Custom Apps
    'core',
]

# ---------- Middleware ----------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ---------- URL Configuration ----------
ROOT_URLCONF = 'super_shinwari.urls'

# ---------- Templates ----------
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
                # Custom Context Processors
                'core.context_processors.cart_and_branch_context',
                'core.context_processors.cart_item_count',
            ],
        },
    },
]

# ---------- WSGI ----------
WSGI_APPLICATION = 'super_shinwari.wsgi.application'

# ---------- Database ----------
# Development (sqlite) + Deployment (dj_database_url for postgres/heroku etc.)
DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        ssl_require=False
    )
}

# ---------- Password Validation ----------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------- Internationalization ----------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Karachi'
USE_I18N = True
USE_TZ = True

# ---------- Static Files ----------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# ---------- Media Files ----------
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ---------- Default Auto Field ----------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------- Email Backend ----------
# Dev: console backend. Production: SMTP settings configure karo.
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'admin@super-shinwari.com'
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# ---------- Authentication Redirects ----------
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'

# ---------- Languages ----------
LANGUAGES = [
    ('en', 'English'),
    ('ur', 'Urdu'),
]

# ---------- Loyalty Settings ----------
# 2% earn rate; 1 point = Rs 1
LOYALTY_EARN_RATE = Decimal("0.02")
LOYALTY_POINT_VALUE = Decimal("1.0")
