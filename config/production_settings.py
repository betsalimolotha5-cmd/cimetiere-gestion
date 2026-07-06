"""
Configuration pour la production.
"""
from .settings import *

# Sécurité
DEBUG = False
ALLOWED_HOSTS = ['localhost', '127.0.0.1']  # Ajoute ton domaine si tu en as un

# Sécurité supplémentaire
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Session et CSRF
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = True

# Fichiers statiques
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Logging pour production
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'production.log',
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'ERROR',
    },
}