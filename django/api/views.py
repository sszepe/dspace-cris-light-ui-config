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
)


def is_admin(request) -> bool:
    user = request.user
    if hasattr(user, "is_staff"):
        return bool(user.is_staff or getattr(user, "is_superuser", False))
    return bool(getattr(user, "is_admin", False))


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
