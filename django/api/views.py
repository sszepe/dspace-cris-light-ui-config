from __future__ import annotations

import requests
from django.conf import settings
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)

from .models import (
    EntityCluster,
    EntityTypeEntry,
    QuickPreset,
    QuickPresetFilter,
    SiteSettings,
    CollectionMapping,
    MetadataSchema,
    MetadataField,
    SubmissionForm,
    SubmissionFormField,
    SubmissionStepDefinition,
    SubmissionProcess,
    FormLayout,
)
from .serializers import (
    EntityClusterSerializer,
    EntityClusterWriteSerializer,
    EntityTypeEntrySerializer,
    QuickPresetSerializer,
    QuickPresetWriteSerializer,
    QuickPresetFilterSerializer,
    SiteSettingsSerializer,
    CollectionMappingSerializer,
    CollectionMappingWriteSerializer,
    MetadataSchemaSerializer,
    MetadataSchemaDetailSerializer,
    MetadataFieldSerializer,
    SubmissionFormSerializer,
    SubmissionFormListSerializer,
    SubmissionFormFieldSerializer,
    SubmissionStepDefinitionSerializer,
    SubmissionProcessSerializer,
    SubmissionProcessListSerializer,
    FormLayoutSerializer,
    FormLayoutWriteSerializer,
)


def is_admin(request) -> bool:
    """
    Returns True if the authenticated user has admin/staff privileges.

    Handles two auth backends:
      - CockpitSessionAuthentication → standard Django User with is_staff/is_superuser
      - DSpaceJWTAuthentication      → DSpaceUser with is_admin property
    """
    user = request.user
    if user is None:
        return False
    # Django User (session auth from cockpit)
    if hasattr(user, "is_staff"):
        return bool(user.is_staff or getattr(user, "is_superuser", False))
    # DSpaceUser (JWT auth from main frontend)
    return bool(getattr(user, "is_admin", False))


# ── Auth diagnostic ────────────────────────────────────────────────────────────

@extend_schema(
    tags=["auth"],
    summary="Debug DSpace authentication",
    description="Diagnostic endpoint that checks whether the supplied bearer token is accepted by DSpace.",
    responses={200: OpenApiResponse(description="Authentication debug payload")},
)
class DebugAuthView(APIView):
    """GET /debug/auth/ — diagnostic probe for DSpace JWT auth."""
    permission_classes = [AllowAny]

    def get(self, request):
        base = settings.DSPACE_BASE_URL.rstrip("/")
        auth = request.META.get("HTTP_AUTHORIZATION", "")
        jwt = auth[len("Bearer "):].strip() if auth.startswith("Bearer ") else None
        dspace_reachable = False
        dspace_status = None
        dspace_authed = None
        auth_error = None
        try:
            headers = {"Authorization": f"Bearer {jwt}"} if jwt else {}
            r = requests.get(f"{base}/api/authn/status", headers=headers, timeout=5)
            dspace_status = r.status_code
            dspace_reachable = True
            if r.status_code == 200:
                dspace_authed = r.json().get("authenticated", False)
        except Exception as e:
            auth_error = str(e)

        return Response({
            "django_reachable": True,
            "dspace_base_url": base,
            "dspace_reachable": dspace_reachable,
            "dspace_status_code": dspace_status,
            "dspace_authenticated": dspace_authed,
            "jwt_received": bool(jwt),
            "jwt_preview": (jwt[:12] + "…") if jwt else None,
            "auth_error": auth_error,
            "settings_module": getattr(settings, "DJANGO_SETTINGS_MODULE", None),
        })


# Keep function alias for URL compatibility
debug_auth = DebugAuthView.as_view()


# ── Dashboard config ───────────────────────────────────────────────────────────

@extend_schema(
    tags=["dashboard"],
    summary="Get dashboard configuration",
    responses={200: OpenApiResponse(description="Enabled dashboard clusters")},
)
class DashboardConfigView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        clusters = EntityCluster.objects.filter(enabled=True).prefetch_related("entity_types")
        return Response({"clusters": EntityClusterSerializer(clusters, many=True).data})


# ── Cluster CRUD ───────────────────────────────────────────────────────────────

@extend_schema_view(
    get=extend_schema(
        tags=["clusters"],
        summary="List clusters",
        responses={200: EntityClusterSerializer(many=True)},
    ),
    post=extend_schema(
        tags=["clusters"],
        summary="Create cluster",
        request=EntityClusterWriteSerializer,
        responses={201: EntityClusterSerializer},
    ),
)
class ClusterListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = EntityCluster.objects.prefetch_related("entity_types").order_by("sort_order", "label")
        return Response(EntityClusterSerializer(qs, many=True).data)

    def post(self, request):
        if not is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        ser = EntityClusterWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return Response(EntityClusterSerializer(ser.save()).data, status=201)


@extend_schema_view(
    get=extend_schema(
        tags=["clusters"],
        summary="Retrieve cluster",
        responses={200: EntityClusterSerializer},
    ),
    patch=extend_schema(
        tags=["clusters"],
        summary="Update cluster",
        request=EntityClusterWriteSerializer,
        responses={200: EntityClusterSerializer},
    ),
    delete=extend_schema(
        tags=["clusters"],
        summary="Delete cluster",
        responses={204: OpenApiResponse(description="Deleted")},
    ),
)
class ClusterDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, pk):
        try:
            return EntityCluster.objects.prefetch_related("entity_types").get(pk=pk)
        except EntityCluster.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get(pk)
        return Response(EntityClusterSerializer(obj).data) if obj else Response(status=404)

    def patch(self, request, pk):
        if not is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj:
            return Response(status=404)
        ser = EntityClusterWriteSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        return Response(EntityClusterSerializer(ser.save()).data)

    def delete(self, request, pk):
        if not is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj:
            return Response(status=404)
        obj.delete()
        return Response(status=204)


@extend_schema(
    tags=["clusters"],
    summary="Add entity type to cluster",
    request=EntityTypeEntrySerializer,
    responses={201: EntityTypeEntrySerializer},
)
class ClusterEntityTypeCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, cluster_id):
        if not is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        try:
            cluster = EntityCluster.objects.get(pk=cluster_id)
        except EntityCluster.DoesNotExist:
            return Response(status=404)

        entry = EntityTypeEntry.objects.create(
            cluster=cluster,
            entity_type_label=request.data.get("entity_type_label", ""),
            sort_order=request.data.get("sort_order", 0),
        )
        return Response(EntityTypeEntrySerializer(entry).data, status=201)


@extend_schema_view(
    patch=extend_schema(
        tags=["clusters"],
        summary="Update cluster entity type",
        request=EntityTypeEntrySerializer,
        responses={200: EntityTypeEntrySerializer},
    ),
    delete=extend_schema(
        tags=["clusters"],
        summary="Delete cluster entity type",
        responses={204: OpenApiResponse(description="Deleted")},
    ),
)
class EntityTypeDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, pk):
        try:
            return EntityTypeEntry.objects.get(pk=pk)
        except EntityTypeEntry.DoesNotExist:
            return None

    def patch(self, request, pk):
        if not is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj:
            return Response(status=404)
        for field in ["entity_type_label", "sort_order"]:
            if field in request.data:
                setattr(obj, field, request.data[field])
        obj.save()
        return Response(EntityTypeEntrySerializer(obj).data)

    def delete(self, request, pk):
        if not is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj:
            return Response(status=404)
        obj.delete()
        return Response(status=204)


# ── Site settings ──────────────────────────────────────────────────────────────

@extend_schema_view(
    get=extend_schema(
        tags=["site-settings"],
        summary="Get site settings",
        responses={200: SiteSettingsSerializer},
    ),
    patch=extend_schema(
        tags=["site-settings"],
        summary="Update site settings",
        request=SiteSettingsSerializer,
        responses={200: SiteSettingsSerializer},
    ),
)
class SiteSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(SiteSettingsSerializer(SiteSettings.get()).data)

    def patch(self, request):
        if not is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        ser = SiteSettingsSerializer(SiteSettings.get(), data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        return Response(SiteSettingsSerializer(ser.save()).data)


# ── Collection mappings ────────────────────────────────────────────────────────

@extend_schema_view(
    get=extend_schema(
        tags=["collection-mappings"],
        summary="List collection mappings",
        parameters=[
            OpenApiParameter(
                name="entity_type",
                required=False,
                type=str,
                description="Filter by DSpace entity type",
            ),
        ],
        responses={200: CollectionMappingSerializer(many=True)},
    ),
    post=extend_schema(
        tags=["collection-mappings"],
        summary="Create collection mapping",
        request=CollectionMappingWriteSerializer,
        responses={201: CollectionMappingSerializer},
    ),
)
class CollectionMappingListCreateView(APIView):
    """
    GET  /collection-mappings/  — list all rules (ordered by sort_order)
    POST /collection-mappings/  — create a new rule (admin only)

    Response shape matches what collection-mapping.ts expects:
      { id, entity_type, collection_id, label, conditions, sort_order, … }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = CollectionMapping.objects.all()
        et = request.query_params.get("entity_type", "").strip()
        if et:
            qs = qs.filter(entity_type__iexact=et)
        return Response(CollectionMappingSerializer(qs, many=True).data)

    def post(self, request):
        if not is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        ser = CollectionMappingWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        obj = ser.save()
        return Response(CollectionMappingSerializer(obj).data, status=201)


@extend_schema_view(
    get=extend_schema(
        tags=["collection-mappings"],
        summary="Retrieve collection mapping",
        responses={200: CollectionMappingSerializer},
    ),
    patch=extend_schema(
        tags=["collection-mappings"],
        summary="Update collection mapping",
        request=CollectionMappingWriteSerializer,
        responses={200: CollectionMappingSerializer},
    ),
    delete=extend_schema(
        tags=["collection-mappings"],
        summary="Delete collection mapping",
        responses={204: OpenApiResponse(description="Deleted")},
    ),
)
class CollectionMappingDetailView(APIView):
    """
    GET    /collection-mappings/{id}/  — single rule
    PATCH  /collection-mappings/{id}/  — update (admin only)
    DELETE /collection-mappings/{id}/  — delete (admin only)
    """
    permission_classes = [IsAuthenticated]

    def _get(self, pk):
        try:
            return CollectionMapping.objects.get(pk=pk)
        except CollectionMapping.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response(status=404)
        return Response(CollectionMappingSerializer(obj).data)

    def patch(self, request, pk):
        if not is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj:
            return Response(status=404)
        ser = CollectionMappingWriteSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        return Response(CollectionMappingSerializer(ser.save()).data)

    def delete(self, request, pk):
        if not is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj:
            return Response(status=404)
        obj.delete()
        return Response(status=204)


# ── Quicklinks ─────────────────────────────────────────────────────────────────

@extend_schema(
    tags=["quickpresets"],
    summary="Quicklinks config",
    responses={200: OpenApiResponse(description="Quicklinks configuration with presets")},
)
class QuicklinksConfigView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        presets = QuickPreset.objects.prefetch_related("filters").order_by("sort_order", "label")
        return Response({"presets": QuickPresetSerializer(presets, many=True).data})


@extend_schema_view(
    get=extend_schema(
        tags=["quickpresets"],
        summary="List quick presets",
        responses={200: QuickPresetSerializer(many=True)},
    ),
    post=extend_schema(
        tags=["quickpresets"],
        summary="Create quick preset",
        request=QuickPresetWriteSerializer,
        responses={201: QuickPresetSerializer},
    ),
)
class QuickPresetListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        presets = QuickPreset.objects.prefetch_related("filters").order_by("sort_order", "label")
        return Response(QuickPresetSerializer(presets, many=True).data)

    def post(self, request):
        if not is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        ser = QuickPresetWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return Response(QuickPresetSerializer(ser.save()).data, status=201)


@extend_schema_view(
    get=extend_schema(
        tags=["quickpresets"],
        summary="Retrieve quick preset",
        responses={200: QuickPresetSerializer},
    ),
    patch=extend_schema(
        tags=["quickpresets"],
        summary="Update quick preset",
        request=QuickPresetWriteSerializer,
        responses={200: QuickPresetSerializer},
    ),
    delete=extend_schema(
        tags=["quickpresets"],
        summary="Delete quick preset",
        responses={204: OpenApiResponse(description="Deleted")},
    ),
)
class QuickPresetDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, pk):
        try:
            return QuickPreset.objects.prefetch_related("filters").get(pk=pk)
        except QuickPreset.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get(pk)
        return Response(QuickPresetSerializer(obj).data) if obj else Response(status=404)

    def patch(self, request, pk):
        if not is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj:
            return Response(status=404)
        ser = QuickPresetWriteSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        return Response(QuickPresetSerializer(ser.save()).data)

    def delete(self, request, pk):
        if not is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj:
            return Response(status=404)
        obj.delete()
        return Response(status=204)


@extend_schema(
    tags=["quickpresets"],
    summary="Add filter to quick preset",
    request=QuickPresetFilterSerializer,
    responses={201: QuickPresetFilterSerializer},
)
class QuickPresetFilterCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, preset_id):
        if not is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        try:
            preset = QuickPreset.objects.get(pk=preset_id)
        except QuickPreset.DoesNotExist:
            return Response(status=404)

        obj = QuickPresetFilter.objects.create(
            preset=preset,
            key=request.data.get("key", ""),
            label=request.data.get("label", ""),
            facet_name=request.data.get("facet_name", ""),
            kind=request.data.get("kind", "text"),
            placeholder=request.data.get("placeholder", ""),
            sort_order=request.data.get("sort_order", 0),
        )
        return Response(QuickPresetFilterSerializer(obj).data, status=201)


@extend_schema_view(
    patch=extend_schema(
        tags=["quickpresets"],
        summary="Update quick preset filter",
        request=QuickPresetFilterSerializer,
        responses={200: QuickPresetFilterSerializer},
    ),
    delete=extend_schema(
        tags=["quickpresets"],
        summary="Delete quick preset filter",
        responses={204: OpenApiResponse(description="Deleted")},
    ),
)
class QuickPresetFilterDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, pk):
        try:
            return QuickPresetFilter.objects.get(pk=pk)
        except QuickPresetFilter.DoesNotExist:
            return None

    def patch(self, request, pk):
        if not is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj:
            return Response(status=404)
        for field in ["key", "label", "facet_name", "kind", "placeholder", "sort_order"]:
            if field in request.data:
                setattr(obj, field, request.data[field])
        obj.save()
        return Response(QuickPresetFilterSerializer(obj).data)

    def delete(self, request, pk):
        if not is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj:
            return Response(status=404)
        obj.delete()
        return Response(status=204)


# ── Submission forms (read-only — populated by import management command) ─────

@extend_schema(
    tags=["submission-forms"],
    summary="List submission forms",
    responses={200: SubmissionFormListSerializer(many=True)},
)
class SubmissionFormListView(APIView):
    """GET /submission-forms/ — list all imported submission forms."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        forms = SubmissionForm.objects.all()
        return Response(SubmissionFormListSerializer(forms, many=True).data)


@extend_schema(
    tags=["submission-forms"],
    summary="Retrieve submission form",
    responses={200: SubmissionFormSerializer},
)
class SubmissionFormDetailView(APIView):
    """GET /submission-forms/{id}/ — full form with all fields."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            form = SubmissionForm.objects.prefetch_related("fields").get(pk=pk)
        except SubmissionForm.DoesNotExist:
            return Response(status=404)
        return Response(SubmissionFormSerializer(form).data)


@extend_schema(
    tags=["submission-forms"],
    summary="List submission form fields",
    description="Returns all fields for a submission form, enriched with metadata registry information when available.",
    responses={
        200: OpenApiResponse(
            description="Submission form fields enriched with optional registry metadata"
        )
    },
)
class SubmissionFormFieldListView(APIView):
    """GET /submission-forms/{form_id}/fields/ — fields for a form, with metadata lookup."""
    permission_classes = [IsAuthenticated]

    def get(self, request, form_id):
        try:
            form = SubmissionForm.objects.get(pk=form_id)
        except SubmissionForm.DoesNotExist:
            return Response(status=404)

        fields = form.fields.select_related("child_form").all()
        result = []
        field_names = {f.field for f in fields if f.field}
        registry_map = {
            mf.field: mf
            for mf in MetadataField.objects.filter(field__in=field_names).select_related("schema")
        }

        for field_obj in fields:
            data = SubmissionFormFieldSerializer(field_obj).data
            reg = registry_map.get(field_obj.field)
            if reg:
                data["registry"] = {
                    "schema": reg.schema.name,
                    "element": reg.element,
                    "qualifier": reg.qualifier,
                    "scope_note": reg.scope_note,
                }
            result.append(data)

        return Response(result)


# ── Form layouts ───────────────────────────────────────────────────────────────

@extend_schema_view(
    get=extend_schema(
        tags=["form-layouts"],
        summary="List form layouts",
        parameters=[
            OpenApiParameter("form_name", str, required=False, description="Filter by form name"),
            OpenApiParameter("profile", str, required=False, description="Filter by profile"),
            OpenApiParameter("collection", str, required=False, description="Filter by collection UUID"),
        ],
        responses={200: FormLayoutSerializer(many=True)},
    ),
    post=extend_schema(
        tags=["form-layouts"],
        summary="Create form layout",
        request=FormLayoutWriteSerializer,
        responses={201: FormLayoutSerializer},
    ),
)
class FormLayoutListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = FormLayout.objects.prefetch_related(
            "sections__field_overrides",
            "conditional_blocks",
        )
        form_name = request.query_params.get("form_name")
        profile = request.query_params.get("profile")
        collection = request.query_params.get("collection")
        if form_name:
            qs = qs.filter(form_name=form_name)
        if profile:
            qs = qs.filter(profile=profile)
        if collection:
            qs = qs.filter(collection=collection)
        return Response(FormLayoutSerializer(qs, many=True).data)

    def post(self, request):
        if not is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        ser = FormLayoutWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        layout = ser.save()
        obj = FormLayout.objects.prefetch_related(
            "sections__field_overrides",
            "conditional_blocks",
        ).get(pk=layout.pk)
        return Response(FormLayoutSerializer(obj).data, status=201)


@extend_schema_view(
    get=extend_schema(
        tags=["form-layouts"],
        summary="Retrieve form layout",
        responses={200: FormLayoutSerializer},
    ),
    patch=extend_schema(
        tags=["form-layouts"],
        summary="Update form layout",
        request=FormLayoutWriteSerializer,
        responses={200: FormLayoutSerializer},
    ),
    delete=extend_schema(
        tags=["form-layouts"],
        summary="Delete form layout",
        responses={204: OpenApiResponse(description="Deleted")},
    ),
)
class FormLayoutDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, pk):
        try:
            return FormLayout.objects.prefetch_related(
                "sections__field_overrides",
                "conditional_blocks",
            ).get(pk=pk)
        except FormLayout.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get(pk)
        return Response(FormLayoutSerializer(obj).data) if obj else Response(status=404)

    def patch(self, request, pk):
        if not is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj:
            return Response(status=404)
        ser = FormLayoutWriteSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(FormLayoutSerializer(self._get(pk)).data)

    def delete(self, request, pk):
        if not is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj:
            return Response(status=404)
        obj.delete()
        return Response(status=204)


# ── Metadata registry (read-only) ─────────────────────────────────────────────

@extend_schema(
    tags=["metadata"],
    summary="List metadata schemas",
    parameters=[
        OpenApiParameter("q", str, required=False, description="Search by schema name"),
    ],
    responses={200: MetadataSchemaSerializer(many=True)},
)
class MetadataSchemaListView(APIView):
    """GET /metadata-schemas/ — list all schemas with field counts."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = MetadataSchema.objects.all()
        q = request.query_params.get("q", "").strip()
        if q:
            qs = qs.filter(name__icontains=q)
        return Response(MetadataSchemaSerializer(qs, many=True).data)


@extend_schema(
    tags=["metadata"],
    summary="Retrieve metadata schema",
    responses={200: MetadataSchemaDetailSerializer},
)
class MetadataSchemaDetailView(APIView):
    """GET /metadata-schemas/{id}/ — schema with all fields."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            schema = MetadataSchema.objects.get(pk=pk)
        except MetadataSchema.DoesNotExist:
            return Response(status=404)
        return Response(MetadataSchemaDetailSerializer(schema).data)


@extend_schema(
    tags=["metadata"],
    summary="List metadata fields",
    parameters=[
        OpenApiParameter(name="q", required=False, type=str, description="Search term"),
        OpenApiParameter(name="schema", required=False, type=str, description="Schema name"),
        OpenApiParameter(name="page", required=False, type=int, description="Zero-based page"),
        OpenApiParameter(name="page_size", required=False, type=int, description="Page size, max 500"),
    ],
    responses={200: OpenApiResponse(description="Paginated metadata field results")},
)
class MetadataFieldListView(APIView):
    """GET /metadata-fields/?q=dc.title&schema=dc&page=0&page_size=200 — field lookup with pagination."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = MetadataField.objects.select_related("schema").order_by("field")
        q = request.query_params.get("q", "").strip()
        schema = request.query_params.get("schema", "").strip()
        if q:
            qs = qs.filter(field__icontains=q)
        if schema:
            qs = qs.filter(schema__name=schema)

        total = qs.count()

        try:
            page_size = min(int(request.query_params.get("page_size", 200)), 500)
        except Exception:
            page_size = 200

        try:
            page = max(int(request.query_params.get("page", 0)), 0)
        except Exception:
            page = 0

        offset = page * page_size
        qs = qs[offset: offset + page_size]

        return Response({
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size,
            "results": MetadataFieldSerializer(qs, many=True).data,
        })


# ── Submission processes (read-only — populated by import management command) ─

@extend_schema(
    tags=["submission-processes"],
    summary="List submission step definitions",
    parameters=[
        OpenApiParameter("q", str, required=False, description="Search by step id"),
        OpenApiParameter("type", str, required=False, description="Filter by step type"),
    ],
    responses={200: SubmissionStepDefinitionSerializer(many=True)},
)
class SubmissionStepDefinitionListView(APIView):
    """GET /submission-step-definitions/ — list all imported step definitions."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = SubmissionStepDefinition.objects.all()
        q = request.query_params.get("q", "").strip()
        type_ = request.query_params.get("type", "").strip()
        if q:
            qs = qs.filter(step_id__icontains=q)
        if type_:
            qs = qs.filter(type=type_)
        return Response(SubmissionStepDefinitionSerializer(qs, many=True).data)


@extend_schema(
    tags=["submission-processes"],
    summary="Retrieve submission step definition",
    responses={200: SubmissionStepDefinitionSerializer},
)
class SubmissionStepDefinitionDetailView(APIView):
    """GET /submission-step-definitions/{id}/ — single step definition."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            obj = SubmissionStepDefinition.objects.get(pk=pk)
        except SubmissionStepDefinition.DoesNotExist:
            return Response(status=404)
        return Response(SubmissionStepDefinitionSerializer(obj).data)


@extend_schema(
    tags=["submission-processes"],
    summary="List submission processes",
    parameters=[
        OpenApiParameter("q", str, required=False, description="Search by process name"),
        OpenApiParameter(
            "detail",
            str,
            required=False,
            description="Set to 1 to embed ordered steps",
        ),
    ],
    responses={200: OpenApiResponse(description="Submission process list or detailed list")},
)
class SubmissionProcessListView(APIView):
    """GET /submission-processes/ — list all imported submission processes."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = SubmissionProcess.objects.prefetch_related("steps__definition")
        q = request.query_params.get("q", "").strip()
        if q:
            qs = qs.filter(name__icontains=q)

        if request.query_params.get("detail") == "1":
            return Response(SubmissionProcessSerializer(qs, many=True).data)
        return Response(SubmissionProcessListSerializer(qs, many=True).data)


@extend_schema(
    tags=["submission-processes"],
    summary="Retrieve submission process",
    responses={200: SubmissionProcessSerializer},
)
class SubmissionProcessDetailView(APIView):
    """GET /submission-processes/{id}/ — full process with ordered steps."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            obj = SubmissionProcess.objects.prefetch_related("steps__definition").get(pk=pk)
        except SubmissionProcess.DoesNotExist:
            return Response(status=404)
        return Response(SubmissionProcessSerializer(obj).data)


# ── Audit views ────────────────────────────────────────────────────────────────

@extend_schema(
    tags=["audit"],
    summary="Audit field usage",
    responses={200: OpenApiResponse(description="Cross-reference of submission fields against metadata registry")},
)
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
            if not field_name:
                continue

            forms = list(
                SubmissionFormField.objects
                .filter(field=field_name)
                .values_list("form__name", flat=True)
                .distinct()
            )
            has_vocabulary = SubmissionFormField.objects.filter(
                field=field_name
            ).exclude(vocabulary="").exists()

            results.append({
                "field": field_name,
                "form_count": row["form_count"],
                "forms": forms,
                "has_vocabulary": has_vocabulary,
                "in_registry": field_name in registry_fields,
            })

        return Response(results)


audit_field_usage = AuditFieldUsageView.as_view()


@extend_schema(
    tags=["audit"],
    summary="Submission forms summary",
    responses={200: OpenApiResponse(description="Summary of imported submission forms")},
)
class AuditFormsSummaryView(APIView):
    """GET /audit/forms-summary/ — summary of all imported submission forms."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Count

        forms = SubmissionForm.objects.annotate(field_count=Count("fields")).values(
            "id",
            "name",
            "contains_required",
            "field_count",
            "imported_at",
        )
        return Response(list(forms))


audit_forms_summary = AuditFormsSummaryView.as_view()