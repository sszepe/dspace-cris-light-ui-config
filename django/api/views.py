from __future__ import annotations
import requests
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes  # kept for compatibility
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    EntityCluster, EntityTypeEntry,
    QuickPreset, QuickPresetFilter, SiteSettings,
    MetadataSchema, MetadataField,
    SubmissionForm, SubmissionFormField,
    FormLayout, FormSection, FormFieldOverride, FormConditionalBlock,
)
from .serializers import (
    EntityClusterSerializer, EntityClusterWriteSerializer,
    EntityTypeEntrySerializer,
    QuickPresetSerializer, QuickPresetWriteSerializer,
    QuickPresetFilterSerializer, SiteSettingsSerializer,
    MetadataSchemaSerializer, MetadataSchemaDetailSerializer, MetadataFieldSerializer,
    SubmissionFormSerializer, SubmissionFormListSerializer,
    FormLayoutSerializer, FormLayoutWriteSerializer,
    FormSectionSerializer, FormFieldOverrideSerializer, FormConditionalBlockSerializer,
)


def is_admin(request) -> bool:
    return getattr(request.user, "is_admin", False)


# ── Auth diagnostic ────────────────────────────────────────────────────────────

class DebugAuthView(APIView):
    """GET /debug/auth/ — diagnostic probe for DSpace JWT auth."""
    permission_classes = [AllowAny]

    def get(self, request):
        base = settings.DSPACE_BASE_URL.rstrip("/")
        auth = request.META.get("HTTP_AUTHORIZATION", "")
        jwt  = auth[len("Bearer "):].strip() if auth.startswith("Bearer ") else None
        dspace_reachable = False; dspace_status = None; dspace_authed = None; auth_error = None
        try:
            h = {"Authorization": f"Bearer {jwt}"} if jwt else {}
            r = requests.get(f"{base}/api/authn/status", headers=h, timeout=5)
            dspace_status = r.status_code; dspace_reachable = True
            if r.status_code == 200: dspace_authed = r.json().get("authenticated", False)
        except Exception as e: auth_error = str(e)
        return Response({
            "django_reachable": True, "dspace_base_url": base,
            "dspace_reachable": dspace_reachable, "dspace_status_code": dspace_status,
            "dspace_authenticated": dspace_authed, "jwt_received": bool(jwt),
            "jwt_preview": (jwt[:12] + "…") if jwt else None,
            "auth_error": auth_error,
            "settings_module": getattr(settings, "DJANGO_SETTINGS_MODULE", None),
        })

# Keep function alias for URL compatibility
debug_auth = DebugAuthView.as_view()


# ── Dashboard config ───────────────────────────────────────────────────────────

class DashboardConfigView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        clusters = EntityCluster.objects.filter(enabled=True).prefetch_related("entity_types")
        return Response({"clusters": EntityClusterSerializer(clusters, many=True).data})


# ── Cluster CRUD ───────────────────────────────────────────────────────────────

class ClusterListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        qs = EntityCluster.objects.prefetch_related("entity_types").order_by("sort_order", "label")
        return Response(EntityClusterSerializer(qs, many=True).data)
    def post(self, request):
        if not is_admin(request): return Response({"detail": "Admin only."}, status=403)
        ser = EntityClusterWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return Response(EntityClusterSerializer(ser.save()).data, status=201)


class ClusterDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def _get(self, pk):
        try: return EntityCluster.objects.prefetch_related("entity_types").get(pk=pk)
        except EntityCluster.DoesNotExist: return None
    def get(self, request, pk):
        obj = self._get(pk)
        return Response(EntityClusterSerializer(obj).data) if obj else Response(status=404)
    def patch(self, request, pk):
        if not is_admin(request): return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj: return Response(status=404)
        ser = EntityClusterWriteSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        return Response(EntityClusterSerializer(ser.save()).data)
    def delete(self, request, pk):
        if not is_admin(request): return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj: return Response(status=404)
        obj.delete(); return Response(status=204)


class ClusterEntityTypeCreateView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, cluster_id):
        if not is_admin(request): return Response({"detail": "Admin only."}, status=403)
        try: cluster = EntityCluster.objects.get(pk=cluster_id)
        except EntityCluster.DoesNotExist: return Response(status=404)
        entry = EntityTypeEntry.objects.create(
            cluster=cluster,
            entity_type_label=request.data.get("entity_type_label", ""),
            sort_order=request.data.get("sort_order", 0),
        )
        return Response(EntityTypeEntrySerializer(entry).data, status=201)


class EntityTypeDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def _get(self, pk):
        try: return EntityTypeEntry.objects.get(pk=pk)
        except EntityTypeEntry.DoesNotExist: return None
    def patch(self, request, pk):
        if not is_admin(request): return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj: return Response(status=404)
        for f in ["entity_type_label", "sort_order"]:
            if f in request.data: setattr(obj, f, request.data[f])
        obj.save()
        return Response(EntityTypeEntrySerializer(obj).data)
    def delete(self, request, pk):
        if not is_admin(request): return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj: return Response(status=404)
        obj.delete(); return Response(status=204)


# ── Site settings ──────────────────────────────────────────────────────────────

class SiteSettingsView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return Response(SiteSettingsSerializer(SiteSettings.get()).data)
    def patch(self, request):
        if not is_admin(request): return Response({"detail": "Admin only."}, status=403)
        ser = SiteSettingsSerializer(SiteSettings.get(), data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        return Response(SiteSettingsSerializer(ser.save()).data)


# ── Quicklinks ─────────────────────────────────────────────────────────────────

class QuicklinksConfigView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        presets = QuickPreset.objects.prefetch_related("filters").order_by("sort_order", "label")
        return Response({"presets": QuickPresetSerializer(presets, many=True).data})


class QuickPresetListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        presets = QuickPreset.objects.prefetch_related("filters").order_by("sort_order", "label")
        return Response(QuickPresetSerializer(presets, many=True).data)
    def post(self, request):
        if not is_admin(request): return Response({"detail": "Admin only."}, status=403)
        ser = QuickPresetWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return Response(QuickPresetSerializer(ser.save()).data, status=201)


class QuickPresetDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def _get(self, pk):
        try: return QuickPreset.objects.prefetch_related("filters").get(pk=pk)
        except QuickPreset.DoesNotExist: return None
    def get(self, request, pk):
        obj = self._get(pk)
        return Response(QuickPresetSerializer(obj).data) if obj else Response(status=404)
    def patch(self, request, pk):
        if not is_admin(request): return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj: return Response(status=404)
        ser = QuickPresetWriteSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        return Response(QuickPresetSerializer(ser.save()).data)
    def delete(self, request, pk):
        if not is_admin(request): return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj: return Response(status=404)
        obj.delete(); return Response(status=204)


class QuickPresetFilterCreateView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, preset_id):
        if not is_admin(request): return Response({"detail": "Admin only."}, status=403)
        try: preset = QuickPreset.objects.get(pk=preset_id)
        except QuickPreset.DoesNotExist: return Response(status=404)
        f = QuickPresetFilter.objects.create(
            preset=preset,
            key=request.data.get("key", ""),
            label=request.data.get("label", ""),
            facet_name=request.data.get("facet_name", ""),
            kind=request.data.get("kind", "text"),
            placeholder=request.data.get("placeholder", ""),
            sort_order=request.data.get("sort_order", 0),
        )
        return Response(QuickPresetFilterSerializer(f).data, status=201)


class QuickPresetFilterDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def _get(self, pk):
        try: return QuickPresetFilter.objects.get(pk=pk)
        except QuickPresetFilter.DoesNotExist: return None
    def patch(self, request, pk):
        if not is_admin(request): return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj: return Response(status=404)
        for f in ["key", "label", "facet_name", "kind", "placeholder", "sort_order"]:
            if f in request.data: setattr(obj, f, request.data[f])
        obj.save(); return Response(QuickPresetFilterSerializer(obj).data)
    def delete(self, request, pk):
        if not is_admin(request): return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj: return Response(status=404)
        obj.delete(); return Response(status=204)


# ── Submission forms (read-only — populated by import management command) ──────

class SubmissionFormListView(APIView):
    """GET /submission-forms/ — list all imported submission forms."""
    permission_classes = [IsAuthenticated]
    def get(self, request):
        forms = SubmissionForm.objects.all()
        return Response(SubmissionFormListSerializer(forms, many=True).data)


class SubmissionFormDetailView(APIView):
    """GET /submission-forms/{id}/ — full form with all fields."""
    permission_classes = [IsAuthenticated]
    def get(self, request, pk):
        try:
            form = SubmissionForm.objects.prefetch_related("fields").get(pk=pk)
        except SubmissionForm.DoesNotExist:
            return Response(status=404)
        return Response(SubmissionFormSerializer(form).data)


# ── Form layouts ───────────────────────────────────────────────────────────────

class FormLayoutListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        qs = FormLayout.objects.prefetch_related(
            "sections__field_overrides", "conditional_blocks"
        )
        form_name = request.query_params.get("form_name")
        profile   = request.query_params.get("profile")
        collection = request.query_params.get("collection")
        if form_name:  qs = qs.filter(form_name=form_name)
        if profile:    qs = qs.filter(profile=profile)
        if collection: qs = qs.filter(collection=collection)
        return Response(FormLayoutSerializer(qs, many=True).data)

    def post(self, request):
        if not is_admin(request): return Response({"detail": "Admin only."}, status=403)
        ser = FormLayoutWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        layout = ser.save()
        return Response(FormLayoutSerializer(
            FormLayout.objects.prefetch_related("sections__field_overrides", "conditional_blocks").get(pk=layout.pk)
        ).data, status=201)


class FormLayoutDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def _get(self, pk):
        try:
            return FormLayout.objects.prefetch_related(
                "sections__field_overrides", "conditional_blocks"
            ).get(pk=pk)
        except FormLayout.DoesNotExist: return None

    def get(self, request, pk):
        obj = self._get(pk)
        return Response(FormLayoutSerializer(obj).data) if obj else Response(status=404)

    def patch(self, request, pk):
        if not is_admin(request): return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj: return Response(status=404)
        ser = FormLayoutWriteSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(FormLayoutSerializer(self._get(pk)).data)

    def delete(self, request, pk):
        if not is_admin(request): return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj: return Response(status=404)
        obj.delete(); return Response(status=204)



# ── Metadata registry (read-only) ─────────────────────────────────────────────

class MetadataSchemaListView(APIView):
    """GET /metadata-schemas/ — list all schemas with field counts."""
    permission_classes = [IsAuthenticated]
    def get(self, request):
        qs = MetadataSchema.objects.all()
        q = request.query_params.get("q","").strip()
        if q: qs = qs.filter(name__icontains=q)
        return Response(MetadataSchemaSerializer(qs, many=True).data)

class MetadataSchemaDetailView(APIView):
    """GET /metadata-schemas/{id}/ — schema with all fields."""
    permission_classes = [IsAuthenticated]
    def get(self, request, pk):
        try: schema = MetadataSchema.objects.get(pk=pk)
        except MetadataSchema.DoesNotExist: return Response(status=404)
        return Response(MetadataSchemaDetailSerializer(schema).data)

class MetadataFieldListView(APIView):
    """GET /metadata-fields/?q=dc.title&schema=dc — field lookup with autocomplete."""
    permission_classes = [IsAuthenticated]
    def get(self, request):
        qs = MetadataField.objects.select_related("schema")
        q      = request.query_params.get("q","").strip()
        schema = request.query_params.get("schema","").strip()
        if q:      qs = qs.filter(field__icontains=q)
        if schema: qs = qs.filter(schema__name=schema)
        qs = qs[:100]  # cap at 100 for autocomplete
        return Response(MetadataFieldSerializer(qs, many=True).data)


# ── Enhanced submission form endpoints ────────────────────────────────────────

class SubmissionFormFieldListView(APIView):
    """GET /submission-forms/{form_id}/fields/ — fields for a form, with metadata lookup."""
    permission_classes = [IsAuthenticated]
    def get(self, request, form_id):
        try: form = SubmissionForm.objects.get(pk=form_id)
        except SubmissionForm.DoesNotExist: return Response(status=404)
        fields = form.fields.select_related("child_form").all()
        # Optionally annotate with metadata registry info
        result = []
        field_names = {f.field for f in fields if f.field}
        registry_map = {
            mf.field: mf for mf in
            MetadataField.objects.filter(field__in=field_names).select_related("schema")
        }
        for f in fields:
            data = SubmissionFormFieldSerializer(f).data
            reg = registry_map.get(f.field)
            if reg:
                data["registry"] = {
                    "schema": reg.schema.name,
                    "element": reg.element,
                    "qualifier": reg.qualifier,
                    "scope_note": reg.scope_note,
                }
            result.append(data)
        return Response(result)


# ── Audit views ────────────────────────────────────────────────────────────────

class AuditFieldUsageView(APIView):
    """GET /audit/field-usage/ — cross-reference fields vs metadata registry."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Count
        fields_qs = (
            SubmissionFormField.objects
            .values("field")
            .annotate(form_count=Count("form", distinct=True))
            .order_by("-form_count", "field")
        )
        registry_fields = set(MetadataField.objects.values_list("field", flat=True))
        results = []
        for row in fields_qs:
            field_name = row["field"]
            if not field_name: continue
            forms = list(
                SubmissionFormField.objects
                .filter(field=field_name)
                .values_list("form__name", flat=True).distinct()
            )
            has_vocabulary = SubmissionFormField.objects.filter(
                field=field_name).exclude(vocabulary="").exists()
            results.append({
                "field": field_name,
                "form_count": row["form_count"],
                "forms": forms,
                "has_vocabulary": has_vocabulary,
                "in_registry": field_name in registry_fields,
            })
        return Response(results)

audit_field_usage = AuditFieldUsageView.as_view()


class AuditFormsSummaryView(APIView):
    """GET /audit/forms-summary/ — summary of all imported submission forms."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Count
        forms = SubmissionForm.objects.annotate(field_count=Count("fields")).values(
            "id", "name", "contains_required", "field_count", "imported_at"
        )
        return Response(list(forms))

audit_forms_summary = AuditFormsSummaryView.as_view()
