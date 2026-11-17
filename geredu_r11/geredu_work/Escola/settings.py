from pathlib import Path
import os
from dotenv import load_dotenv
import dj_database_url

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


# ==================================================
# SEGURANÇA
# ==================================================

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")

DEBUG = os.environ.get("DEBUG", "True") == "True"

ALLOWED_HOSTS = [
    os.environ.get("RAILWAY_PUBLIC_DOMAIN", ""),
    ".railway.app",
    "127.0.0.1",
    "localhost",
]

ALLOWED_HOSTS = [host for host in ALLOWED_HOSTS if host]

CSRF_TRUSTED_ORIGINS = []

if os.environ.get("RAILWAY_PUBLIC_DOMAIN"):
    CSRF_TRUSTED_ORIGINS.append(
        f"https://{os.environ.get('RAILWAY_PUBLIC_DOMAIN')}"
    )

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True


# ==================================================
# APLICAÇÕES
# ==================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "storages",
    "widget_tweaks",
    "django_htmx",
    "core",
    "usuarios",
    "alunos",
    "turmas",
    "ocorrencias",
    "frequencia",
    'transferencias',
    "conselho",
    "busca_ativa",
    "acompanhamento_avaliacoes",
]


# ==================================================
# MIDDLEWARE
# ==================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "escola.urls"
WSGI_APPLICATION = "escola.wsgi.application"


# ==================================================
# TEMPLATES
# ==================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
            BASE_DIR / "escola" / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.estatisticas_alunos",
                "core.context_processors.alertas_infrequencia",
                "core.context_processors.avisos_e_calendario",
            ],
        },
    },
]


# ==================================================
# BANCO DE DADOS (Railway + PostgreSQL LOCAL)
# ==================================================

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME", "escola"),
            "USER": os.environ.get("DB_USER", "postgres"),
            "PASSWORD": os.environ.get("DB_PASSWORD", "123456"),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "5432"),
        }
    }


# ==================================================
# USUÁRIO CUSTOMIZADO
# ==================================================

AUTH_USER_MODEL = "usuarios.Usuario"

AUTHENTICATION_BACKENDS = [
    "usuarios.auth_backends.CPFOrUsernameBackend",
    "django.contrib.auth.backends.ModelBackend",
]


# ==================================================
# LOGIN
# ==================================================

LOGIN_URL = "/usuarios/login/"
LOGOUT_REDIRECT_URL = "/usuarios/login/"
LOGIN_REDIRECT_URL = "/"


# ==================================================
# PASSWORD VALIDATION
# ==================================================

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ==================================================
# INTERNACIONALIZAÇÃO
# ==================================================

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Cuiaba"
USE_I18N = True
USE_TZ = True


# ==================================================
# STATIC FILES
# ==================================================

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"


# ==================================================
# FOTO PADRÃO DO ALUNO
# ==================================================

FOTO_PADRAO_ALUNO = "img/aluno_sem_foto.png"


# ==================================================
# EMAIL
# ==================================================

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True

EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER


# ==================================================
# CLOUDFARE R2 STORAGE
# ==================================================

# Credenciais do Cloudflare R2. Em desenvolvimento local, quando o R2 não
# estiver configurado, os uploads usam MEDIA_ROOT (armazenamento local). Em
# produção, a ausência de qualquer variável obrigatória interrompe a inicialização
# para evitar que arquivos sejam gravados silenciosamente em disco efêmero.
AWS_ACCESS_KEY_ID = (os.getenv("AWS_ACCESS_KEY_ID") or "").strip()
AWS_SECRET_ACCESS_KEY = (os.getenv("AWS_SECRET_ACCESS_KEY") or "").strip()
AWS_STORAGE_BUCKET_NAME = (os.getenv("AWS_STORAGE_BUCKET_NAME") or "").strip()
AWS_S3_ENDPOINT_URL = (os.getenv("AWS_S3_ENDPOINT_URL") or "").strip()
AWS_S3_REGION_NAME = (os.getenv("AWS_S3_REGION_NAME") or "auto").strip()

AWS_S3_SIGNATURE_VERSION = "s3v4"
AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = True
AWS_QUERYSTRING_EXPIRE = 3600
AWS_S3_FILE_OVERWRITE = False
AWS_S3_ADDRESSING_STYLE = "path"
AWS_S3_VERIFY = True

R2_CONFIGURADO = all((
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_STORAGE_BUCKET_NAME,
    AWS_S3_ENDPOINT_URL,
))

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

if R2_CONFIGURADO:
    ARQUIVOS_BACKEND = "storages.backends.s3boto3.S3Boto3Storage"
else:
    if not DEBUG:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured(
            "Cloudflare R2 não configurado. Defina AWS_ACCESS_KEY_ID, "
            "AWS_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME e AWS_S3_ENDPOINT_URL."
        )
    # Fallback intencional apenas para desenvolvimento/testes locais.
    ARQUIVOS_BACKEND = "django.core.files.storage.FileSystemStorage"

DEFAULT_FILE_STORAGE = ARQUIVOS_BACKEND

STORAGES = {
    "default": {"BACKEND": ARQUIVOS_BACKEND},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}


# ==================================================
# PADRÃO AUTO FIELD
# ==================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ==================================================
# UPLOAD DE ARQUIVOS
# ==================================================

DATA_UPLOAD_MAX_MEMORY_SIZE = 524288000
FILE_UPLOAD_MAX_MEMORY_SIZE = 524288000