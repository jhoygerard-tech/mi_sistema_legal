import os
from pathlib import Path
from dotenv import load_dotenv
from django.contrib.messages import constants as messages

# ══════════════════════════════════════════════
# SEGURIDAD
# ══════════════════════════════════════════════
load_dotenv()  # carga el .env automáticamente

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
DEBUG      = True
ALLOWED_HOSTS = []

# ══════════════════════════════════════════════
# APLICACIONES
# ══════════════════════════════════════════════
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'control_legal',
    'usuarios',
]


# ══════════════════════════════════════════════
# MIDDLEWARE
# ══════════════════════════════════════════════
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# ══════════════════════════════════════════════
# URLS Y WSGI
# ══════════════════════════════════════════════
ROOT_URLCONF      = 'mi_sistema_legal.urls'
WSGI_APPLICATION  = 'mi_sistema_legal.wsgi.application'


# ══════════════════════════════════════════════
# TEMPLATES
# ══════════════════════════════════════════════
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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


# ══════════════════════════════════════════════
# BASE DE DATOS
# ══════════════════════════════════════════════
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# ══════════════════════════════════════════════
# VALIDACIÓN DE CONTRASEÑAS
# ══════════════════════════════════════════════
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ══════════════════════════════════════════════
# IDIOMA Y ZONA HORARIA — BOLIVIA
# ══════════════════════════════════════════════
LANGUAGE_CODE = 'es'
TIME_ZONE     = 'America/La_Paz'
USE_I18N      = True
USE_TZ        = True


# ══════════════════════════════════════════════
# ARCHIVOS ESTÁTICOS Y MEDIA
# ══════════════════════════════════════════════
STATIC_URL = '/static/'
MEDIA_URL  = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# ══════════════════════════════════════════════
# AUTENTICACIÓN
# ══════════════════════════════════════════════
LOGIN_URL           = 'login'
LOGIN_REDIRECT_URL  = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'


# ══════════════════════════════════════════════
# MENSAJES FLASH — BOOTSTRAP 5
# ══════════════════════════════════════════════
MESSAGE_TAGS = {
    messages.DEBUG:   'secondary',
    messages.INFO:    'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR:   'danger',
}


# ══════════════════════════════════════════════
# CLAVE PRIMARIA POR DEFECTO
# ══════════════════════════════════════════════
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

GEMINI_API_KEY='AIzaSyDt6r7suDjOSAk7OHp8RzVXCDDIG9Dw3-g'