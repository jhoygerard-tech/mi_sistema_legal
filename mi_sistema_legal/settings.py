import os
from pathlib import Path
from dotenv import load_dotenv
from django.contrib.messages import constants as messages

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

#SEGURIDAD
# ADVERTENCIA DE SEGURIDAD: Cambiar esta clave antes de pasar a producción.
# Generá una nueva con: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') 
SECRET_KEY = os.environ.get('SECRET_KEY') 

# CORRECCIÓN: DEBUG debe ser False en producción
DEBUG = True

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'control_legal',
    'usuarios',   # CORRECCIÓN: habilitada (el app existe con modelos y urls)
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'mi_sistema_legal.urls'

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

WSGI_APPLICATION = 'mi_sistema_legal.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Idioma y zona horaria Bolivia
LANGUAGE_CODE = 'es'
TIME_ZONE     = 'America/La_Paz'
USE_I18N      = True
USE_TZ        = True

# Archivos estáticos y subidos
# CORRECCIÓN: eliminadas las definiciones duplicadas que sobreescribían valores
STATIC_URL  = 'static/'
MEDIA_URL   = '/media/'
MEDIA_ROOT  = BASE_DIR / 'media'

# Autenticación
LOGIN_URL            = 'login'
LOGIN_REDIRECT_URL   = 'dashboard'
LOGOUT_REDIRECT_URL  = 'login'

# Colores de mensajes flash para Bootstrap
from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.DEBUG:   'secondary',
    messages.INFO:    'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR:   'danger',
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Gemini AI
# ADVERTENCIA DE SEGURIDAD: Mover esta clave a una variable de entorno antes de producción.
# Usar: os.environ.get('GEMINI_API_KEY')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')