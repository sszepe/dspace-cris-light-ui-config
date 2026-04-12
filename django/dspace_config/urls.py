from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # ── Config Cockpit auth (Django session, no DSpace JWT) ───────────────
    path("api/cockpit/auth/", include("cockpit.urls")),

    # ── Main config API (DSpace JWT auth) ─────────────────────────────────
    path("api/dspace-config/", include("api.urls")),

    # ── DSpace CRSI Layout ─────────────────────────────────────────────────────
    path("api/dspace-config/cris-layout/", include("cris_layout.urls")),

    # ── OpenAPI schema ─────────────────────────────────────────────────────
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]
