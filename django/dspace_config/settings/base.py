import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "change-me-in-production")
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1,django").split(",")

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "rest_framework", "corsheaders", "django_filters", "drf_spectacular", "api", "cockpit",
    "cris_layout",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # serves static files
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "dspace_config.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [],
    "APP_DIRS": True, "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]}}]
WSGI_APPLICATION = "dspace_config.wsgi.application"

DATABASES = {"default": {
    "ENGINE":   "django.db.backends.postgresql",
    "NAME":     os.environ.get("DB_NAME",     "django_config"),
    "USER":     os.environ.get("DB_USER",     "dspace"),
    "PASSWORD": os.environ.get("DB_PASSWORD", "dspace"),
    "HOST":     os.environ.get("DB_HOST",     "localhost"),
    "PORT":     os.environ.get("DB_PORT",     "5432"),
}}

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise — serve compressed static files directly from Gunicorn
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["cockpit.authentication.CockpitSessionAuthentication","api.authentication.DSpaceJWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES":     ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES":       ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_FILTER_BACKENDS":        ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_SCHEMA_CLASS":           "drf_spectacular.openapi.AutoSchema",
}

_cors = os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:4000,http://localhost:5174")
CORS_ALLOWED_ORIGINS   = [o.strip() for o in _cors.split(",") if o.strip()]
CORS_ALLOW_CREDENTIALS = True
DSPACE_BASE_URL = os.environ.get("DSPACE_BASE_URL", "http://localhost:8080/server")

# Suppress AutoField warnings — use BigAutoField for all models
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# drf-spectacular (OpenAPI schema generation)
SPECTACULAR_SETTINGS = {
    "TITLE": "DSpace CRIS Config API",
    "DESCRIPTION": (
        "Configuration API for the DSpace CRIS light client.\n\n"
        "Authentication uses a bearer token issued by DSpace and passed as:\n"
        "`Authorization: Bearer <token>`"
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/dspace-config",
    "SWAGGER_UI_SETTINGS": {
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "docExpansion": "list",
    },
    "TAGS": [
        {"name": "auth", "description": "Authentication and diagnostics"},
        {"name": "dashboard", "description": "Dashboard configuration"},
        {"name": "clusters", "description": "Dashboard entity clusters"},
        {"name": "site-settings", "description": "Global UI feature flags"},
        {"name": "collection-mappings", "description": "Entity type to collection mapping rules"},
        {"name": "quickpresets", "description": "Quicklink preset configuration"},
        {"name": "submission-forms", "description": "Imported submission forms"},
        {"name": "submission-processes", "description": "Imported submission processes"},
        {"name": "form-layouts", "description": "Form layout overrides"},
        {"name": "metadata", "description": "Metadata registry lookup"},
        {"name": "audit", "description": "Audit and reporting endpoints"},
    ],
}
