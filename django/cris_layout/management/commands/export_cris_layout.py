"""
Management command: export_cris_layout

Exports the current cris_layout database contents back to an XLS file
that matches the original cris-layout-configuration.xls format exactly,
including the i18n auto-generated sheets.

Usage
-----
    python manage.py export_cris_layout output.xls
    python manage.py export_cris_layout output.xlsx
    python manage.py export_cris_layout output.xls --entity Person,Publication
"""
from __future__ import annotations

import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
except ImportError:
    openpyxl = None  # type: ignore

from cris_layout.models import (
    CrisLayoutTab, CrisLayoutTab2Box, CrisLayoutBox,
    CrisLayoutBox2Metadata, CrisLayoutBox2Metrics,
    CrisLayoutBox2Vocabulary, CrisLayoutMetadataGroup,
    CrisLayoutTabPolicy, CrisLayoutBoxPolicy,
)

HEADER_FILL = PatternFill("solid", start_color="003b79", end_color="003b79")
HEADER_FONT = Font(bold=True, color="FFFFFF", name="Arial", size=10)
BODY_FONT   = Font(name="Arial", size=10)
ALT_FILL    = PatternFill("solid", start_color="EEF4FB", end_color="EEF4FB")
BORDER_SIDE = Side(style="thin", color="C3D5E8")
THIN_BORDER = Border(
    left=BORDER_SIDE, right=BORDER_SIDE, top=BORDER_SIDE, bottom=BORDER_SIDE
)


def _ws(wb, title: str):
    ws = wb.create_sheet(title=title)
    return ws


def _header(ws, cols: list[str]):
    ws.append(cols)
    for cell in ws[1]:
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 18


def _row(ws, values: list, alt: bool = False):
    ws.append(values)
    row_idx = ws.max_row
    fill = ALT_FILL if alt else None
    for cell in ws[row_idx]:
        cell.font = BODY_FONT
        if fill:
            cell.fill = fill


def _col_widths(ws, widths: dict[str, int]):
    for col, w in widths.items():
        ws.column_dimensions[col].width = w


def yn(val: bool) -> str:
    return "y" if val else "n"


class Command(BaseCommand):
    help = "Export DSpace CRIS layout configuration to XLS/XLSX"

    def add_arguments(self, parser):
        parser.add_argument("output_file", help="Output path (.xlsx recommended)")
        parser.add_argument(
            "--entity", default="",
            help="Comma-separated list of entities to export (default: all)",
        )

    def handle(self, *args, **options):
        if openpyxl is None:
            raise CommandError("openpyxl is required: pip install openpyxl")

        out_path = options["output_file"]
        entity_filter = (
            {e.strip() for e in options["entity"].split(",") if e.strip()}
            if options["entity"] else None
        )

        def qs_filter(qs):
            if entity_filter:
                return qs.filter(entity__in=entity_filter)
            return qs

        wb = openpyxl.Workbook()
        wb.remove(wb.active)  # remove default blank sheet

        # ── tab ──────────────────────────────────────────────────────────────
        ws = _ws(wb, "tab")
        _header(ws, ["ENTITY", "SHORTNAME", "LABEL", "PRIORITY", "LEADING", "SECURITY"])
        for i, t in enumerate(qs_filter(CrisLayoutTab.objects.all())):
            _row(ws, [t.entity, t.shortname, t.label, t.priority, yn(t.leading), t.security], i % 2)
        _col_widths(ws, {"A": 14, "B": 20, "C": 22, "D": 10, "E": 9, "F": 22})

        # ── tab2box ───────────────────────────────────────────────────────────
        ws = _ws(wb, "tab2box")
        _header(ws, ["ENTITY", "TAB", "ROW", "ROW_STYLE", "CELL_STYLE", "BOXES"])
        for i, t in enumerate(qs_filter(CrisLayoutTab2Box.objects.all())):
            _row(ws, [t.entity, t.tab, t.row, t.row_style, t.cell_style, t.boxes], i % 2)
        _col_widths(ws, {"A": 14, "B": 28, "C": 6, "D": 18, "E": 18, "F": 40})

        # ── box ───────────────────────────────────────────────────────────────
        ws = _ws(wb, "box")
        _header(ws, ["ENTITY", "COLLAPSED", "TYPE", "SHORTNAME", "LABEL", "CONTAINER", "MINOR", "SECURITY", "STYLE"])
        for i, b in enumerate(qs_filter(CrisLayoutBox.objects.all())):
            _row(ws, [
                b.entity, yn(b.collapsed), b.box_type,
                b.shortname, b.label, yn(b.container),
                yn(b.minor), b.security, b.style,
            ], i % 2)
        _col_widths(ws, {"A": 14, "B": 10, "C": 12, "D": 20, "E": 28, "F": 10, "G": 8, "H": 22, "I": 18})

        # ── box2hierarchicalvocabulary ────────────────────────────────────────
        ws = _ws(wb, "box2hierarchicalvocabulary")
        _header(ws, ["ENTITY", "BOX", "VOCABULARY", "METADATA"])
        for i, v in enumerate(qs_filter(CrisLayoutBox2Vocabulary.objects.all())):
            _row(ws, [v.entity, v.box, v.vocabulary, v.metadata], i % 2)
        _col_widths(ws, {"A": 14, "B": 20, "C": 30, "D": 40})

        # ── box2metadata ──────────────────────────────────────────────────────
        ws = _ws(wb, "box2metadata")
        _header(ws, [
            "ENTITY", "BOX", "ROW", "CELL", "FIELDTYPE", "METADATA",
            "VALUE", "BUNDLE", "LABEL", "LABEL_AS_HEADING", "RENDERING",
            "VALUES_INLINE", "ROW_STYLE", "CELL_STYLE", "STYLE_LABEL", "STYLE_VALUE",
        ])
        for i, f in enumerate(qs_filter(CrisLayoutBox2Metadata.objects.all())):
            _row(ws, [
                f.entity, f.box, f.row, f.cell, f.field_type,
                f.metadata, f.value, f.bundle, f.label,
                yn(f.label_as_heading), f.rendering, yn(f.values_inline),
                f.row_style, f.cell_style, f.style_label, f.style_value,
            ], i % 2)
        _col_widths(ws, {"A": 14, "B": 20, "C": 6, "D": 6, "E": 14, "F": 38,
                         "G": 20, "H": 14, "I": 28, "J": 16, "K": 28,
                         "L": 14, "M": 16, "N": 16, "O": 24, "P": 20})

        # ── metadatagroups ────────────────────────────────────────────────────
        ws = _ws(wb, "metadatagroups")
        _header(ws, ["ENTITY", "PARENT", "FIELDTYPE", "METADATA", "VALUE",
                     "BUNDLE", "LABEL", "RENDERING", "STYLE_LABEL", "STYLE_VALUE"])
        for i, g in enumerate(qs_filter(CrisLayoutMetadataGroup.objects.all())):
            _row(ws, [
                g.entity, g.parent, g.field_type, g.metadata,
                g.value, g.bundle, g.label, g.rendering,
                g.style_label, g.style_value,
            ], i % 2)
        _col_widths(ws, {"A": 14, "B": 38, "C": 14, "D": 38, "E": 14,
                         "F": 14, "G": 28, "H": 20, "I": 22, "J": 20})

        # ── box2metrics ───────────────────────────────────────────────────────
        ws = _ws(wb, "box2metrics")
        _header(ws, ["ENTITY", "BOX", "METRIC_TYPE"])
        for i, m in enumerate(qs_filter(CrisLayoutBox2Metrics.objects.all())):
            _row(ws, [m.entity, m.box, m.metric_type], i % 2)
        _col_widths(ws, {"A": 14, "B": 20, "C": 80})

        # ── tabpolicy ─────────────────────────────────────────────────────────
        ws = _ws(wb, "tabpolicy")
        _header(ws, ["ENTITY", "SHORTNAME", "METADATA", "GROUP"])
        for i, p in enumerate(qs_filter(CrisLayoutTabPolicy.objects.all())):
            _row(ws, [p.entity, p.shortname, p.metadata, p.group], i % 2)
        _col_widths(ws, {"A": 14, "B": 20, "C": 38, "D": 24})

        # ── boxpolicy ─────────────────────────────────────────────────────────
        ws = _ws(wb, "boxpolicy")
        _header(ws, ["ENTITY", "SHORTNAME", "METADATA", "GROUP"])
        for i, p in enumerate(qs_filter(CrisLayoutBoxPolicy.objects.all())):
            _row(ws, [p.entity, p.shortname, p.metadata, p.group], i % 2)
        _col_widths(ws, {"A": 14, "B": 20, "C": 38, "D": 24})

        # ── utilsdata (reference, static) ─────────────────────────────────────
        ws = _ws(wb, "utilsdata")
        _header(ws, ["BOX-TYPES", "METADATA-RENDERING", "Security"])
        for row_data in [
            ["RELATION", "heading", "PUBLIC"],
            ["METADATA", "text", "ADMINISTRATOR"],
            ["METRICS", "longtext", "OWNER ONLY"],
            ["IIIFVIEWER", "link", "OWNER & ADMINISTRATOR"],
            ["", "link.label", "CUSTOM DATA"],
            ["", "date", "CUSTOM DATA & ADMINISTRATOR"],
            ["", "identifier", ""],
            ["", "crisref", ""],
            ["", "thumbnail", ""],
            ["", "attachment", ""],
            ["", "tag", ""],
        ]:
            ws.append(row_data)
            for cell in ws[ws.max_row]:
                cell.font = BODY_FONT

        # ── i18n sheets (auto-generated keys) ─────────────────────────────────
        def make_i18n(sheet_name, prefix, items):
            ws = _ws(wb, sheet_name)
            ws.append(["PREFIX", "AUTOGENERATED I18N keys"])
            ws["A1"].font = HEADER_FONT
            ws["A1"].fill = HEADER_FILL
            ws["B1"].font = HEADER_FONT
            ws["B1"].fill = HEADER_FILL
            ws.append([prefix, ""])
            for key in items:
                ws.append(["", key])
            # pad to 1000 rows like the original
            current = ws.max_row
            for _ in range(max(0, 1000 - current)):
                ws.append(["", ""])
            ws.column_dimensions["A"].width = 24
            ws.column_dimensions["B"].width = 60

        tab_keys = [
            f"{t.entity.lower()}.{t.shortname}"
            for t in qs_filter(CrisLayoutTab.objects.all())
        ]
        make_i18n("tab_i18n", "layout.tab.header.", tab_keys)

        box_keys = [
            f"{b.entity.lower()}.{b.shortname}"
            for b in qs_filter(CrisLayoutBox.objects.all())
        ]
        make_i18n("box_i18n", "layout.box.header.", box_keys)

        meta_keys = list({
            f.metadata
            for f in qs_filter(CrisLayoutBox2Metadata.objects.all())
            if f.metadata
        })
        make_i18n("metadata_i18n", "layout.field.label.", sorted(meta_keys))

        mg_keys = list({
            f.metadata
            for f in qs_filter(CrisLayoutMetadataGroup.objects.all())
            if f.metadata
        })
        make_i18n("metadatagroup_i18n", "layout.field.label.", sorted(mg_keys))

        wb.save(out_path)
        self.stdout.write(self.style.SUCCESS(f"Exported to: {out_path}"))
