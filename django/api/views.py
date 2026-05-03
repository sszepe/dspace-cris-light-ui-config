from __future__ import annotations
import io
import requests
import tempfile
from pathlib import Path
from django.conf import settings
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    EntityCluster, EntityTypeEntry,
    QuickPreset, QuickPresetFilter, SiteSettings,
    CollectionMapping,
    MetadataSchema, MetadataField,
    SubmissionForm, SubmissionFormField,
    SubmissionStepDefinition, SubmissionProcess, SubmissionProcessStep,
    FormLayout, FormSection, FormFieldOverride, FormConditionalBlock,
    SubmissionValuePairSet, SubmissionValuePair,
)
from .serializers import (
    EntityClusterSerializer, EntityClusterWriteSerializer,
    EntityTypeEntrySerializer,
    QuickPresetSerializer, QuickPresetWriteSerializer,
    QuickPresetFilterSerializer, SiteSettingsSerializer,
    CollectionMappingSerializer, CollectionMappingWriteSerializer,
    MetadataSchemaSerializer, MetadataSchemaDetailSerializer, MetadataFieldSerializer,
    SubmissionFormSerializer, SubmissionFormListSerializer, SubmissionFormFieldSerializer,
    SubmissionStepDefinitionSerializer,
    SubmissionProcessSerializer, SubmissionProcessListSerializer,
    SubmissionProcessStepSerializer,
    FormLayoutSerializer, FormLayoutWriteSerializer,
    FormSectionSerializer, FormFieldOverrideSerializer, FormConditionalBlockSerializer,
    SubmissionValuePairSetSerializer,
    SubmissionValuePairSetListSerializer,
    SubmissionValuePairSerializer,
)


def is_admin(request) -> bool:
    user = request.user
    if hasattr(user, "is_staff"):
        return bool(user.is_staff or getattr(user, "is_superuser", False))
    return bool(getattr(user, "is_admin", False))


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _ts_esc(s: str) -> str:
    return (s or "").replace("\\", "\\\\").replace('"', '\\"')


# ── Auth diagnostic ────────────────────────────────────────────────────────────

class DebugAuthView(APIView):
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
            "jwt_preview": (jwt[:12] + "…") if jwt else None, "auth_error": auth_error,
        })

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


# ── Collection mappings ────────────────────────────────────────────────────────

class CollectionMappingListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        qs = CollectionMapping.objects.all().order_by("sort_order", "entity_type")
        return Response(CollectionMappingSerializer(qs, many=True).data)
    def post(self, request):
        if not is_admin(request): return Response({"detail": "Admin only."}, status=403)
        ser = CollectionMappingWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return Response(CollectionMappingSerializer(ser.save()).data, status=201)

class CollectionMappingDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def _get(self, pk):
        try: return CollectionMapping.objects.get(pk=pk)
        except CollectionMapping.DoesNotExist: return None
    def get(self, request, pk):
        obj = self._get(pk)
        return Response(CollectionMappingSerializer(obj).data) if obj else Response(status=404)
    def patch(self, request, pk):
        if not is_admin(request): return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj: return Response(status=404)
        ser = CollectionMappingWriteSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        return Response(CollectionMappingSerializer(ser.save()).data)
    def delete(self, request, pk):
        if not is_admin(request): return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj: return Response(status=404)
        obj.delete(); return Response(status=204)


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


# ── Submission forms ───────────────────────────────────────────────────────────

class SubmissionFormListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return Response(SubmissionFormListSerializer(SubmissionForm.objects.all(), many=True).data)

class SubmissionFormDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, pk):
        try: form = SubmissionForm.objects.prefetch_related("fields").get(pk=pk)
        except SubmissionForm.DoesNotExist: return Response(status=404)
        return Response(SubmissionFormSerializer(form).data)

class SubmissionFormFieldListView(APIView):
    """GET /submission-forms/{form_id}/fields/ — fields with metadata registry lookup."""
    permission_classes = [IsAuthenticated]
    def get(self, request, form_id):
        try: form = SubmissionForm.objects.get(pk=form_id)
        except SubmissionForm.DoesNotExist: return Response(status=404)
        fields = form.fields.order_by("row", "col")
        registry_map = {
            mf.field: mf for mf in MetadataField.objects.filter(
                field__in=fields.values_list("field", flat=True)
            ).select_related("schema")
        }
        result = []
        for f in fields:
            data = SubmissionFormFieldSerializer(f).data
            reg = registry_map.get(f.field)
            if reg:
                data["registry"] = {
                    "schema": reg.schema.name, "element": reg.element,
                    "qualifier": reg.qualifier, "scope_note": reg.scope_note,
                }
            result.append(data)
        return Response(result)

class SubmissionFormFieldDetailView(APIView):
    """PATCH /submission-forms/fields/{pk}/ — edit a single form field."""
    permission_classes = [IsAuthenticated]
    def _get(self, pk):
        try: return SubmissionFormField.objects.get(pk=pk)
        except SubmissionFormField.DoesNotExist: return None
    def patch(self, request, pk):
        if not is_admin(request): return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj: return Response(status=404)
        allowed = [
            "label", "input_type", "is_required", "required_msg",
            "repeatable", "vocabulary", "vocabulary_closed",
            "value_pairs_name", "hint", "style", "regex", "row", "col",
        ]
        for field in allowed:
            if field in request.data: setattr(obj, field, request.data[field])
        obj.save()
        return Response(SubmissionFormFieldSerializer(obj).data)


# ── Submission form export ─────────────────────────────────────────────────────

class SubmissionFormExportView(APIView):
    """GET /submission-forms/export/?format=xml|ts[&forms=name1,name2]"""
    permission_classes = [IsAuthenticated]
    def get(self, request):
        from django.core.management import call_command
        from django.http import HttpResponse
        fmt = request.query_params.get("format", "xml").lower()
        forms_param = request.query_params.get("forms", "")
        if fmt not in ("xml", "ts"):
            return Response({"detail": "format must be xml or ts"}, status=400)
        with tempfile.NamedTemporaryFile(
                suffix=".xml" if fmt == "xml" else ".ts", delete=False) as tmp:
            tmp_path = tmp.name
        kwargs = {"stdout": io.StringIO(), "stderr": io.StringIO()}
        if fmt == "xml": kwargs["out_xml"] = tmp_path; kwargs["skip_ts"] = True
        else: kwargs["out_ts"] = tmp_path; kwargs["skip_xml"] = True
        if forms_param: kwargs["forms"] = forms_param
        call_command("export_submission_forms", **kwargs)
        content = Path(tmp_path).read_bytes()
        Path(tmp_path).unlink(missing_ok=True)
        ct = "application/xml" if fmt == "xml" else "text/plain"
        fname = "submission-forms.xml" if fmt == "xml" else "submission-config.ts"
        resp = HttpResponse(content, content_type=ct)
        resp["Content-Disposition"] = f'attachment; filename="{fname}"'; return resp


# ── Submission processes ───────────────────────────────────────────────────────

class SubmissionStepDefinitionListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return Response(SubmissionStepDefinitionSerializer(
            SubmissionStepDefinition.objects.all(), many=True).data)

class SubmissionStepDefinitionDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, pk):
        try: obj = SubmissionStepDefinition.objects.get(pk=pk)
        except SubmissionStepDefinition.DoesNotExist: return Response(status=404)
        return Response(SubmissionStepDefinitionSerializer(obj).data)

class SubmissionProcessListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return Response(SubmissionProcessListSerializer(
            SubmissionProcess.objects.all(), many=True).data)

class SubmissionProcessDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, pk):
        try: obj = SubmissionProcess.objects.prefetch_related("steps__definition").get(pk=pk)
        except SubmissionProcess.DoesNotExist: return Response(status=404)
        return Response(SubmissionProcessSerializer(obj).data)

class SubmissionProcessStepDetailView(APIView):
    """PATCH /submission-process-steps/{pk}/ — reorder a step."""
    permission_classes = [IsAuthenticated]
    def _get(self, pk):
        try: return SubmissionProcessStep.objects.get(pk=pk)
        except SubmissionProcessStep.DoesNotExist: return None
    def patch(self, request, pk):
        if not is_admin(request): return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj: return Response(status=404)
        if "sort_order" in request.data:
            obj.sort_order = int(request.data["sort_order"]); obj.save()
        return Response(SubmissionProcessStepSerializer(obj).data)


# ── Submission process export ──────────────────────────────────────────────────

class SubmissionProcessExportView(APIView):
    """GET /submission-processes/export/?format=xml|ts[&processes=name1,name2]"""
    permission_classes = [IsAuthenticated]
    def get(self, request):
        from django.core.management import call_command
        from django.http import HttpResponse
        fmt = request.query_params.get("format", "xml").lower()
        procs_param = request.query_params.get("processes", "")
        if fmt not in ("xml", "ts"):
            return Response({"detail": "format must be xml or ts"}, status=400)
        with tempfile.NamedTemporaryFile(
                suffix=".xml" if fmt == "xml" else ".ts", delete=False) as tmp:
            tmp_path = tmp.name
        kwargs = {"stdout": io.StringIO(), "stderr": io.StringIO()}
        if fmt == "xml": kwargs["out_xml"] = tmp_path; kwargs["skip_ts"] = True
        else: kwargs["out_ts"] = tmp_path; kwargs["skip_xml"] = True
        if procs_param: kwargs["processes"] = procs_param
        call_command("export_submission_processes", **kwargs)
        content = Path(tmp_path).read_bytes()
        Path(tmp_path).unlink(missing_ok=True)
        ct = "application/xml" if fmt == "xml" else "text/plain"
        fname = "item-submission.xml" if fmt == "xml" else "item-submission.ts"
        resp = HttpResponse(content, content_type=ct)
        resp["Content-Disposition"] = f'attachment; filename="{fname}"'; return resp


# ── Form layouts ───────────────────────────────────────────────────────────────

class FormLayoutListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        qs = FormLayout.objects.prefetch_related("sections__field_overrides", "conditional_blocks")
        for param in ("form_name", "profile", "collection"):
            val = request.query_params.get(param)
            if val: qs = qs.filter(**{param: val})
        return Response(FormLayoutSerializer(qs, many=True).data)
    def post(self, request):
        if not is_admin(request): return Response({"detail": "Admin only."}, status=403)
        ser = FormLayoutWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        layout = ser.save()
        return Response(FormLayoutSerializer(
            FormLayout.objects.prefetch_related(
                "sections__field_overrides", "conditional_blocks").get(pk=layout.pk)
        ).data, status=201)

class FormLayoutDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def _get(self, pk):
        try: return FormLayout.objects.prefetch_related(
            "sections__field_overrides", "conditional_blocks").get(pk=pk)
        except FormLayout.DoesNotExist: return None
    def get(self, request, pk):
        obj = self._get(pk)
        return Response(FormLayoutSerializer(obj).data) if obj else Response(status=404)
    def patch(self, request, pk):
        if not is_admin(request): return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj: return Response(status=404)
        ser = FormLayoutWriteSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True); ser.save()
        return Response(FormLayoutSerializer(self._get(pk)).data)
    def delete(self, request, pk):
        if not is_admin(request): return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj: return Response(status=404)
        obj.delete(); return Response(status=204)


# ── Metadata registry (read-only) ─────────────────────────────────────────────

class MetadataSchemaListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        qs = MetadataSchema.objects.all()
        q = request.query_params.get("q", "").strip()
        if q: qs = qs.filter(name__icontains=q)
        return Response(MetadataSchemaSerializer(qs, many=True).data)

class MetadataSchemaDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, pk):
        try: schema = MetadataSchema.objects.get(pk=pk)
        except MetadataSchema.DoesNotExist: return Response(status=404)
        return Response(MetadataSchemaDetailSerializer(schema).data)

class MetadataFieldListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        qs = MetadataField.objects.select_related("schema")
        q      = request.query_params.get("q", "").strip()
        schema = request.query_params.get("schema", "").strip()
        if q:      qs = qs.filter(field__icontains=q)
        if schema: qs = qs.filter(schema__name=schema)
        return Response(MetadataFieldSerializer(qs[:100], many=True).data)


# ── Audit ──────────────────────────────────────────────────────────────────────

class AuditFieldUsageView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        from django.db.models import Count
        fields_qs = (SubmissionFormField.objects
            .values("field").annotate(form_count=Count("form", distinct=True))
            .order_by("-form_count", "field"))
        registry_fields = set(MetadataField.objects.values_list("field", flat=True))
        results = []
        for row in fields_qs:
            fn = row["field"]
            if not fn: continue
            forms = list(SubmissionFormField.objects.filter(field=fn)
                .values_list("form__name", flat=True).distinct())
            has_vocab = SubmissionFormField.objects.filter(field=fn).exclude(vocabulary="").exists()
            results.append({"field": fn, "form_count": row["form_count"],
                "forms": forms, "has_vocabulary": has_vocab, "in_registry": fn in registry_fields})
        return Response(results)

audit_field_usage = AuditFieldUsageView.as_view()


class AuditFormsSummaryView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        from django.db.models import Count
        forms = SubmissionForm.objects.annotate(field_count=Count("fields")).values(
            "id", "name", "contains_required", "field_count", "imported_at")
        return Response(list(forms))

audit_forms_summary = AuditFormsSummaryView.as_view()

class DiscoveryXmlExportView(APIView):
    """
    GET /api/dspace-config/discovery-xml/
    Returns discovery.xml patched with all QuickPreset facets as bean
    definitions registered in defaultConfiguration.
    Requires DISCOVERY_XML_BASE in Django settings.
    """
    permission_classes = [IsAuthenticated]
 
    def get(self, request):
        import io as _io
        import tempfile as _tmp
        from pathlib import Path as _Path
        from django.conf import settings as _settings
        from django.core.management import call_command
        from django.http import HttpResponse
 
        base_file = request.query_params.get("base", "")
        if not base_file:
            base_file = getattr(_settings, "DISCOVERY_XML_BASE", "")
 
        if not base_file or not _Path(base_file).exists():
            return Response(
                {"detail": (
                    f"Base discovery.xml not found at '{base_file}'. "
                    "Set DISCOVERY_XML_BASE in settings.py or pass ?base=/path."
                )},
                status=400,
            )
 
        with _tmp.NamedTemporaryFile(suffix=".xml", delete=False) as tmp:
            tmp_path = tmp.name
 
        call_command(
            "export_discovery_xml",
            base_file=base_file,
            output_file=tmp_path,
            stdout=_io.StringIO(),
            stderr=_io.StringIO(),
        )
 
        content = _Path(tmp_path).read_bytes()
        _Path(tmp_path).unlink(missing_ok=True)
 
        response = HttpResponse(content, content_type="application/xml")
        response["Content-Disposition"] = 'attachment; filename="discovery.xml"'
        return response

# ── Key Value Pairs ─────────────────────────────────────────────────────────

def _get_set_or_404(pk: int) -> SubmissionValuePairSet:
    try:
        return SubmissionValuePairSet.objects.prefetch_related("pairs").get(pk=pk)
    except SubmissionValuePairSet.DoesNotExist:
        from rest_framework.exceptions import NotFound
        raise NotFound(f"Value-pair set {pk} not found.")


def _get_pair_or_404(pk: int) -> SubmissionValuePair:
    try:
        return SubmissionValuePair.objects.select_related("pair_set").get(pk=pk)
    except SubmissionValuePair.DoesNotExist:
        from rest_framework.exceptions import NotFound
        raise NotFound(f"Value pair {pk} not found.")


class ValuePairSetListCreate(APIView):
    """
    GET  /value-pair-sets/   — list all sets (lightweight, no pairs array)
    POST /value-pair-sets/   — create a new set
    """
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        sets = SubmissionValuePairSet.objects.prefetch_related("pairs").all()
        serializer = SubmissionValuePairSetListSerializer(sets, many=True)
        return Response(serializer.data)

    def post(self, request: Request) -> Response:
        serializer = SubmissionValuePairSetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ValuePairSetDetail(APIView):
    """
    GET    /value-pair-sets/{pk}/  — retrieve a set with its full pairs array
    PATCH  /value-pair-sets/{pk}/  — update set metadata (name, dc_term, note)
    DELETE /value-pair-sets/{pk}/  — delete set and cascade-delete all its pairs
    """
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, pk: int) -> Response:
        obj = _get_set_or_404(pk)
        return Response(SubmissionValuePairSetSerializer(obj).data)

    def patch(self, request: Request, pk: int) -> Response:
        obj = _get_set_or_404(pk)
        serializer = SubmissionValuePairSetSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request: Request, pk: int) -> Response:
        obj = _get_set_or_404(pk)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ValuePairSetReplacePairs(APIView):
    """
    POST /value-pair-sets/{pk}/replace-pairs/

    Body: {"pairs": [{"displayed_value": "…", "stored_value": "…"}, …]}

    Atomically replaces all pairs for the set.  Returns the updated set
    (with the new pairs array) so the frontend can re-sync without an
    extra round-trip.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, pk: int) -> Response:
        obj = _get_set_or_404(pk)
        raw_pairs = request.data.get("pairs")
        if not isinstance(raw_pairs, list):
            return Response(
                {"error": "'pairs' must be a JSON array."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            obj.pairs.all().delete()
            for i, p in enumerate(raw_pairs):
                SubmissionValuePair.objects.create(
                    pair_set=obj,
                    sort_order=i,
                    displayed_value=str(p.get("displayed_value", "")),
                    stored_value=str(p.get("stored_value", "")),
                )

        # Re-fetch to get fresh prefetch
        obj.refresh_from_db()
        obj = _get_set_or_404(pk)
        return Response(SubmissionValuePairSetSerializer(obj).data)


class ValuePairSetExportXml(APIView):
    """
    GET /value-pair-sets/export-xml/

    Downloads all value-pair sets as a <form-value-pairs> XML block
    suitable for embedding in submission-forms.xml.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> HttpResponse:
        lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<form-value-pairs>"]
        for vps in SubmissionValuePairSet.objects.prefetch_related("pairs").all():
            dc = f' dc-term="{_esc(vps.dc_term)}"' if vps.dc_term else ""
            lines.append(f'  <value-pairs value-pairs-name="{_esc(vps.name)}"{dc}>')
            for pair in vps.pairs.all():
                lines.append("    <pair>")
                lines.append(f"      <displayed-value>{_esc(pair.displayed_value)}</displayed-value>")
                lines.append(f"      <stored-value>{_esc(pair.stored_value)}</stored-value>")
                lines.append("    </pair>")
            lines.append("  </value-pairs>")
        lines.append("</form-value-pairs>")

        resp = HttpResponse("\n".join(lines), content_type="application/xml; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="submission-value-pairs.xml"'
        return resp


class ValuePairSetExportTs(APIView):
    """
    GET /value-pair-sets/export-ts/

    Downloads the SUBMISSION_VALUE_PAIRS TypeScript constant — drop this
    file into the dspace-cris frontend as submission-value-pairs.tsx.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> HttpResponse:
        lines = [
            "// Auto-generated by DSpace CRIS Config Cockpit",
            "// Replace submission-value-pairs.tsx in the dspace-cris frontend with this file.",
            "",
            "export type SubmissionValuePair = {",
            "  displayedValue?: string;",
            "  storedValue?: string;",
            "};",
            "",
            "export type SubmissionValuePairsConfig = {",
            "  name: string;",
            "  dcTerm?: string;",
            "  pairs: SubmissionValuePair[];",
            "};",
            "",
            "export const SUBMISSION_VALUE_PAIRS:"
            " Record<string, SubmissionValuePairsConfig> = {",
        ]
        sets = list(SubmissionValuePairSet.objects.prefetch_related("pairs").all())
        for i, vps in enumerate(sets):
            trailing = "," if i < len(sets) - 1 else ""
            lines.append(f"  {vps.name}: {{")
            lines.append(f'    name: "{_ts_esc(vps.name)}",')
            if vps.dc_term:
                lines.append(f'    dcTerm: "{_ts_esc(vps.dc_term)}",')
            lines.append("    pairs: [")
            pairs = list(vps.pairs.all())
            for j, pair in enumerate(pairs):
                pair_trailing = "," if j < len(pairs) - 1 else ""
                lines.append(
                    f'      {{ displayedValue: "{_ts_esc(pair.displayed_value)}",'
                    f' storedValue: "{_ts_esc(pair.stored_value)}" }}{pair_trailing}'
                )
            lines.append("    ],")
            lines.append(f"  }}{trailing}")
        lines.extend([
            "};",
            "",
            "export function getSubmissionValuePairs(",
            "  name: string,",
            "): SubmissionValuePairsConfig | undefined {",
            "  return SUBMISSION_VALUE_PAIRS[name];",
            "}",
        ])

        resp = HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="submission-value-pairs.tsx"'
        return resp


class ValuePairListCreate(APIView):
    """
    GET  /value-pairs/?set=<id>  — list pairs for a given set
    POST /value-pairs/           — create a single pair
                                   Body: {pair_set, displayed_value, stored_value, sort_order}
    """
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        qs = SubmissionValuePair.objects.select_related("pair_set")
        set_id = request.query_params.get("set")
        if set_id:
            qs = qs.filter(pair_set_id=set_id)
        return Response(SubmissionValuePairSerializer(qs, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = SubmissionValuePairSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ValuePairDetail(APIView):
    """
    GET    /value-pairs/{pk}/  — retrieve a single pair
    PATCH  /value-pairs/{pk}/  — update displayed_value / stored_value / sort_order
    DELETE /value-pairs/{pk}/  — remove the pair
    """
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, pk: int) -> Response:
        return Response(SubmissionValuePairSerializer(_get_pair_or_404(pk)).data)

    def patch(self, request: Request, pk: int) -> Response:
        pair = _get_pair_or_404(pk)
        serializer = SubmissionValuePairSerializer(pair, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request: Request, pk: int) -> Response:
        _get_pair_or_404(pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)