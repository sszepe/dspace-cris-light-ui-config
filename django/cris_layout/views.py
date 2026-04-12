"""
cris_layout/views.py

REST API for the CRIS layout configuration.
Mounted under /api/dspace-config/cris-layout/
"""
from __future__ import annotations

import io
import subprocess
import sys
import tempfile
from pathlib import Path

from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    CrisLayoutTab, CrisLayoutTab2Box, CrisLayoutBox,
    CrisLayoutBox2Metadata, CrisLayoutBox2Metrics,
    CrisLayoutBox2Vocabulary, CrisLayoutMetadataGroup,
    CrisLayoutTabPolicy, CrisLayoutBoxPolicy,
)
from .serializers import (
    CrisLayoutTabSerializer, CrisLayoutTab2BoxSerializer,
    CrisLayoutBoxSerializer, CrisLayoutBoxWriteSerializer,
    CrisLayoutBox2MetadataSerializer, CrisLayoutBox2MetricsSerializer,
    CrisLayoutBox2VocabularySerializer, CrisLayoutMetadataGroupSerializer,
    CrisLayoutTabPolicySerializer, CrisLayoutBoxPolicySerializer,
    EntityLayoutSerializer,
)


def _is_admin(request) -> bool:
    user = request.user
    if hasattr(user, "is_staff"):
        return bool(user.is_staff or getattr(user, "is_superuser", False))
    return bool(getattr(user, "is_admin", False))


# ── Entity list ───────────────────────────────────────────────────────────────

class CrisLayoutEntityListView(APIView):
    """GET /cris-layout/entities/ — list distinct entity types."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        entities = sorted(
            CrisLayoutTab.objects.values_list("entity", flat=True).distinct()
        )
        return Response({"entities": entities})


# ── Full entity layout ────────────────────────────────────────────────────────

class CrisLayoutEntityView(APIView):
    """GET /cris-layout/entities/{entity}/ — full layout for one entity."""
    permission_classes = [IsAuthenticated]

    def get(self, request, entity: str):
        tabs    = CrisLayoutTab.objects.filter(entity=entity).order_by("priority")
        tab2box = CrisLayoutTab2Box.objects.filter(entity=entity).order_by("tab", "row")
        boxes   = CrisLayoutBox.objects.filter(entity=entity).order_by("shortname")
        groups  = CrisLayoutMetadataGroup.objects.filter(entity=entity).order_by("parent")
        tab_pol = CrisLayoutTabPolicy.objects.filter(entity=entity)

        # Attach box data inline
        box_data = []
        for box in boxes:
            b_ser = CrisLayoutBoxSerializer(box).data
            # Replace the generic reverse relation with explicit queries
            b_ser["fields_data"] = CrisLayoutBox2MetadataSerializer(
                CrisLayoutBox2Metadata.objects.filter(entity=entity, box=box.shortname)
                .order_by("row", "cell"),
                many=True,
            ).data
            metrics_obj = CrisLayoutBox2Metrics.objects.filter(
                entity=entity, box=box.shortname
            ).first()
            b_ser["metrics"] = (
                CrisLayoutBox2MetricsSerializer(metrics_obj).data if metrics_obj else None
            )
            b_ser["policies"] = CrisLayoutBoxPolicySerializer(
                CrisLayoutBoxPolicy.objects.filter(entity=entity, shortname=box.shortname),
                many=True,
            ).data
            box_data.append(b_ser)

        return Response({
            "entity": entity,
            "tabs": CrisLayoutTabSerializer(tabs, many=True).data,
            "tab2box": CrisLayoutTab2BoxSerializer(tab2box, many=True).data,
            "boxes": box_data,
            "metadata_groups": CrisLayoutMetadataGroupSerializer(groups, many=True).data,
            "tab_policies": CrisLayoutTabPolicySerializer(tab_pol, many=True).data,
        })


# ── Tab CRUD ──────────────────────────────────────────────────────────────────

class CrisLayoutTabListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = CrisLayoutTab.objects.all()
        entity = request.query_params.get("entity", "")
        if entity:
            qs = qs.filter(entity=entity)
        return Response(CrisLayoutTabSerializer(qs, many=True).data)

    def post(self, request):
        if not _is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        ser = CrisLayoutTabSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return Response(CrisLayoutTabSerializer(ser.save()).data, status=201)


class CrisLayoutTabDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, pk):
        try:
            return CrisLayoutTab.objects.get(pk=pk)
        except CrisLayoutTab.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get(pk)
        return Response(CrisLayoutTabSerializer(obj).data) if obj else Response(status=404)

    def patch(self, request, pk):
        if not _is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj:
            return Response(status=404)
        ser = CrisLayoutTabSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        return Response(CrisLayoutTabSerializer(ser.save()).data)

    def delete(self, request, pk):
        if not _is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj:
            return Response(status=404)
        obj.delete()
        return Response(status=204)


# ── Box CRUD ──────────────────────────────────────────────────────────────────

class CrisLayoutBoxListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = CrisLayoutBox.objects.all()
        entity = request.query_params.get("entity", "")
        if entity:
            qs = qs.filter(entity=entity)
        return Response(CrisLayoutBoxSerializer(qs, many=True).data)

    def post(self, request):
        if not _is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        ser = CrisLayoutBoxWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        obj = ser.save()
        return Response(CrisLayoutBoxSerializer(obj).data, status=201)


class CrisLayoutBoxDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, pk):
        try:
            return CrisLayoutBox.objects.get(pk=pk)
        except CrisLayoutBox.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get(pk)
        return Response(CrisLayoutBoxSerializer(obj).data) if obj else Response(status=404)

    def patch(self, request, pk):
        if not _is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj:
            return Response(status=404)
        ser = CrisLayoutBoxWriteSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        obj = ser.save()
        return Response(CrisLayoutBoxSerializer(obj).data)

    def delete(self, request, pk):
        if not _is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj:
            return Response(status=404)
        obj.delete()
        return Response(status=204)


# ── Box→Metadata CRUD ─────────────────────────────────────────────────────────

class CrisLayoutBox2MetadataListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = CrisLayoutBox2Metadata.objects.all()
        for param in ("entity", "box"):
            val = request.query_params.get(param)
            if val:
                qs = qs.filter(**{param: val})
        return Response(CrisLayoutBox2MetadataSerializer(qs, many=True).data)

    def post(self, request):
        if not _is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        ser = CrisLayoutBox2MetadataSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return Response(CrisLayoutBox2MetadataSerializer(ser.save()).data, status=201)


class CrisLayoutBox2MetadataDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, pk):
        try:
            return CrisLayoutBox2Metadata.objects.get(pk=pk)
        except CrisLayoutBox2Metadata.DoesNotExist:
            return None

    def patch(self, request, pk):
        if not _is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj:
            return Response(status=404)
        ser = CrisLayoutBox2MetadataSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        return Response(CrisLayoutBox2MetadataSerializer(ser.save()).data)

    def delete(self, request, pk):
        if not _is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj:
            return Response(status=404)
        obj.delete()
        return Response(status=204)


# ── Tab2Box CRUD ──────────────────────────────────────────────────────────────

class CrisLayoutTab2BoxListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = CrisLayoutTab2Box.objects.all()
        entity = request.query_params.get("entity", "")
        if entity:
            qs = qs.filter(entity=entity)
        return Response(CrisLayoutTab2BoxSerializer(qs, many=True).data)

    def post(self, request):
        if not _is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        ser = CrisLayoutTab2BoxSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return Response(CrisLayoutTab2BoxSerializer(ser.save()).data, status=201)


class CrisLayoutTab2BoxDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, pk):
        try:
            return CrisLayoutTab2Box.objects.get(pk=pk)
        except CrisLayoutTab2Box.DoesNotExist:
            return None

    def patch(self, request, pk):
        if not _is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj:
            return Response(status=404)
        ser = CrisLayoutTab2BoxSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        return Response(CrisLayoutTab2BoxSerializer(ser.save()).data)

    def delete(self, request, pk):
        if not _is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj:
            return Response(status=404)
        obj.delete()
        return Response(status=204)


# ── Metadata Groups CRUD ──────────────────────────────────────────────────────

class CrisLayoutMetadataGroupListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = CrisLayoutMetadataGroup.objects.all()
        for param in ("entity", "parent"):
            val = request.query_params.get(param)
            if val:
                qs = qs.filter(**{param: val})
        return Response(CrisLayoutMetadataGroupSerializer(qs, many=True).data)

    def post(self, request):
        if not _is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        ser = CrisLayoutMetadataGroupSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return Response(CrisLayoutMetadataGroupSerializer(ser.save()).data, status=201)


class CrisLayoutMetadataGroupDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, pk):
        try:
            return CrisLayoutMetadataGroup.objects.get(pk=pk)
        except CrisLayoutMetadataGroup.DoesNotExist:
            return None

    def patch(self, request, pk):
        if not _is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj:
            return Response(status=404)
        ser = CrisLayoutMetadataGroupSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        return Response(CrisLayoutMetadataGroupSerializer(ser.save()).data)

    def delete(self, request, pk):
        if not _is_admin(request):
            return Response({"detail": "Admin only."}, status=403)
        obj = self._get(pk)
        if not obj:
            return Response(status=404)
        obj.delete()
        return Response(status=204)


# ── XLS Export (download) ─────────────────────────────────────────────────────

class CrisLayoutExportView(APIView):
    """GET /cris-layout/export/ — download the current layout as XLSX."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        entity = request.query_params.get("entity", "")
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name

        # Call the export management command programmatically
        from django.core.management import call_command
        kwargs = {"output_file": tmp_path, "stdout": io.StringIO()}
        if entity:
            kwargs["entity"] = entity
        call_command("export_cris_layout", **kwargs)

        with open(tmp_path, "rb") as f:
            content = f.read()
        Path(tmp_path).unlink(missing_ok=True)

        filename = f"cris-layout-configuration.xlsx"
        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
