from django.urls import path
from . import views

# All endpoints under /api/dspace-config/
# VITE_DJANGO_CONFIG_API_BASE_URL=/api/dspace-config (no trailing slash)
# django-client.ts calls e.g. "/site-settings/" → /api/dspace-config/site-settings/

urlpatterns = [
    # ── Auth ────────────────────────────────────────────────────────────────
    path("debug/auth/",                           views.debug_auth,                              name="debug-auth"),

    # ── Dashboard config ─────────────────────────────────────────────────────
    path("dashboard-config/",                     views.DashboardConfigView.as_view(),           name="dashboard-config"),

    # ── Cluster CRUD ─────────────────────────────────────────────────────────
    path("clusters/",                             views.ClusterListCreateView.as_view(),          name="cluster-list"),
    path("clusters/<int:pk>/",                    views.ClusterDetailView.as_view(),              name="cluster-detail"),
    path("clusters/<int:cluster_id>/entity-types/", views.ClusterEntityTypeCreateView.as_view(), name="cluster-entity-type-create"),
    path("entity-types/<int:pk>/",                views.EntityTypeDetailView.as_view(),           name="entity-type-detail"),

    # ── Site settings ─────────────────────────────────────────────────────────
    path("site-settings/",                        views.SiteSettingsView.as_view(),               name="site-settings"),

    # ── Collection mappings ───────────────────────────────────────────────────
    path("collection-mappings/",                  views.CollectionMappingListCreateView.as_view(), name="collection-mapping-list"),
    path("collection-mappings/<int:pk>/",         views.CollectionMappingDetailView.as_view(),     name="collection-mapping-detail"),

    # ── Quicklinks ───────────────────────────────────────────────────────────
    path("quicklinks/",                           views.QuicklinksConfigView.as_view(),           name="quicklinks-config"),
    path("quicklinks/presets/",                   views.QuickPresetListCreateView.as_view(),      name="quicklinks-presets"),
    path("quicklinks/presets/<int:pk>/",          views.QuickPresetDetailView.as_view(),          name="quicklinks-preset-detail"),
    path("quickpresets/",                         views.QuickPresetListCreateView.as_view(),      name="quickpreset-list"),
    path("quickpresets/<int:pk>/",                views.QuickPresetDetailView.as_view(),          name="quickpreset-detail"),
    path("quickpresets/<int:preset_id>/filters/", views.QuickPresetFilterCreateView.as_view(),    name="quickpreset-filter-create"),
    path("quickpreset-filters/<int:pk>/",         views.QuickPresetFilterDetailView.as_view(),    name="quickpreset-filter-detail"),

    # ── Submission forms (read-only, populated by import_plain_config) ────────
    path("submission-forms/",                     views.SubmissionFormListView.as_view(),         name="submission-form-list"),
    path("submission-forms/<int:pk>/",            views.SubmissionFormDetailView.as_view(),       name="submission-form-detail"),
    path("submission-forms/<int:form_id>/fields/",views.SubmissionFormFieldListView.as_view(),    name="submission-form-fields"),

    # ── Submission processes (read-only, populated by import_plain_config) ───
    path("submission-step-definitions/",          views.SubmissionStepDefinitionListView.as_view(),   name="submission-step-definition-list"),
    path("submission-step-definitions/<int:pk>/", views.SubmissionStepDefinitionDetailView.as_view(), name="submission-step-definition-detail"),
    path("submission-processes/",                 views.SubmissionProcessListView.as_view(),           name="submission-process-list"),
    path("submission-processes/<int:pk>/",        views.SubmissionProcessDetailView.as_view(),         name="submission-process-detail"),

    # ── Form layouts ──────────────────────────────────────────────────────────
    path("form-layouts/",                         views.FormLayoutListCreateView.as_view(),       name="form-layout-list"),
    path("form-layouts/<int:pk>/",                views.FormLayoutDetailView.as_view(),           name="form-layout-detail"),

    # ── Metadata registry (read-only, for field autocomplete in form-builder) ──
    path("metadata-schemas/",                     views.MetadataSchemaListView.as_view(),         name="metadata-schema-list"),
    path("metadata-schemas/<int:pk>/",            views.MetadataSchemaDetailView.as_view(),       name="metadata-schema-detail"),
    path("metadata-fields/",                      views.MetadataFieldListView.as_view(),           name="metadata-field-list"),

    # ── Audit ─────────────────────────────────────────────────────────────────
    path("audit/field-usage/",                    views.audit_field_usage,                        name="audit-field-usage"),
    path("audit/forms-summary/",                  views.audit_forms_summary,                      name="audit-forms-summary"),
]
