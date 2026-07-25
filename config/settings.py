"""
Django settings for cimetiere_gestion project.
Conforme au CDC : sécurité, MFA, API REST, PostGIS.
Optimisé pour Render + Neon (hébergement gratuit).
"""
import os
import platform
from pathlib import Path
from decouple import config
import dj_database_url

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# ==============================================================================
# CONFIGURATION GDAL (Pour le développement local sous Windows)
# ==============================================================================
# Cette configuration est ignorée en production (Render/Linux)
# if platform.system() == 'Windows':
    # Indique à Django le chemin exact de la DLL GDAL installée via OSGeo4W
    # ⚠️ IMPORTANT : Vérifie dans C:\OSGeo4W\bin\ le nom exact de ton fichier (ex: gdal305.dll, gdal309.dll, gdal310.dll)
    # et modifie le nom ci-dessous si nécessaire.
    # GDAL_LIBRARY_PATH = r'C:\OSGeo4W\bin\gdal305.dll'
    
    # Optionnel : Si tu as aussi des erreurs sur GEOS, décommente la ligne suivante :
    # GEOS_LIBRARY_PATH = r'C:\OSGeo4W\bin\geos_c.dll'

# ==============================================================================
# SECURITY & DEBUG
# ==============================================================================
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')
DEBUG = config('DEBUG', default=False, cast=bool)

# ALLOWED_HOSTS - Compatible Render (.onrender.com)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,.onrender.com').split(',')

# OBLIGATOIRE POUR RENDER (Sinon erreur 403 sur les formulaires HTTPS)
CSRF_TRUSTED_ORIGINS = [
    'https://cimetiere-gestion.onrender.com',
    'https://*.onrender.com',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# ==============================================================================
# APPLICATION DEFINITION
# ==============================================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',  # ⭐ Indispensable pour PostGIS et les cartes
    
    # Apps tierces
    'rest_framework',
    'drf_spectacular',
    'django_filters',
    'corsheaders',
    'anymail',
    
    # Apps locales
    'apps.accounts',
    'apps.core',
    'apps.billing',
    'apps.notifications',
    'apps.reports',
    'apps.mfa',
    'apps.portal',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
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

WSGI_APPLICATION = 'config.wsgi.application'

# ==============================================================================
# BASE DE DONNÉES (SQLite en local, PostGIS en production via Render)
# ==============================================================================
DATABASE_URL = config('DATABASE_URL', default=None)

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            engine='django.contrib.gis.db.backends.postgis'
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ==============================================================================
# AUTHENTIFICATION & UTILISATEUR (CORE DU MFA)
# ==============================================================================
AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ⭐ CORRECTION CRUCIALE : Forcer l'utilisation des vues MFA
LOGIN_URL = '/mfa/login/'
LOGIN_REDIRECT_URL = '/portal/'
LOGOUT_REDIRECT_URL = '/mfa/login/'

# ==============================================================================
# CONFIGURATION EMAIL (API HTTPS Brevo)
# ==============================================================================
# Utilisation de config() pour éviter le message d'erreur en local si le .env est manquant,
# tout en restant compatible avec les variables d'environnement de Render.
BREVO_API_KEY = config('BREVO_API_KEY', default=os.environ.get('BREVO_API_KEY', ''))
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default=os.environ.get('DEFAULT_FROM_EMAIL', 'betsalimolotha5@gmail.com'))

if BREVO_API_KEY:
    print(f"✅ [SYSTEME] BREVO_API_KEY chargée avec succès. Début: {BREVO_API_KEY[:15]}...")
else:
    print("⚠️ [SYSTEME] BREVO_API_KEY non détectée en local. L'envoi d'email utilisera le mode fallback.")

# ==============================================================================
# INTERNATIONALIZATION & TIMEZONE
# ==============================================================================
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Kinshasa'
USE_I18N = True
USE_TZ = True

# ==============================================================================
# FICHIERS STATIQUES & MÉDIAS
# ==============================================================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==============================================================================
# CORS Configuration
# ==============================================================================
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:8550,http://127.0.0.1:8550,http://localhost:8000,http://127.0.0.1:8000,https://cimetiere-gestion.onrender.com'
).split(',')
CORS_ALLOW_CREDENTIALS = True

# ==============================================================================
# SECURITY SETTINGS (Production)
# ==============================================================================
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'same-origin'

if config('FORCE_HTTPS', default=False, cast=bool):
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ==============================================================================
# CACHE & SESSION
# ==============================================================================
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'cimetiere-cache',
        'TIMEOUT': 600,
        'OPTIONS': {'MAX_ENTRIES': 1000}
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 3600
SESSION_COOKIE_NAME = 'cimetiere_session'
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# ==============================================================================
# LOGGING
# ==============================================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'level': 'DEBUG',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# ==============================================================================
# DJANGO REST FRAMEWORK & SPECTACULAR
# ==============================================================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
    },
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Gestion Cimetière API',
    'DESCRIPTION': 'API REST pour la gestion du cimetière - Conforme au CDC',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# ==============================================================================
# UPLOADS & BACKUPS
# ==============================================================================
BACKUP_DIR = BASE_DIR / 'backups'
if not BACKUP_DIR.exists():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024