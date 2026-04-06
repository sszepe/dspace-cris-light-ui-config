"""
Management command: import_plain_config

Imports plain DSpace CRIS config into Django:
  1. Metadata registry  — MetadataSchema + MetadataField (498 unique fields)
  2. Submission forms   — SubmissionForm + SubmissionFormField (30 forms)

Key fix: uses brace-matched extraction for each field object so qualifier is
read only from within the current field's own {} — not from the next sibling.
This eliminates all duplicate (schema, element, qualifier) constraint violations.

Safe to re-run — uses update_or_create throughout.

Usage:
    python manage.py import_plain_config [--config-dir PATH] [--clear]
    python manage.py import_plain_config --skip-metadata
    python manage.py import_plain_config --skip-forms
"""
import os, re, json
from django.core.management.base import BaseCommand
from django.db import transaction
from api.models import MetadataSchema, MetadataField, SubmissionForm, SubmissionFormField


class Command(BaseCommand):
    help = "Import plain DSpace CRIS config into Django."

    def add_arguments(self, parser):
        parser.add_argument("--config-dir", default="/app/frontend-config")
        parser.add_argument("--clear", action="store_true",
                            help="Clear existing records before importing.")
        parser.add_argument("--skip-metadata", action="store_true")
        parser.add_argument("--skip-forms", action="store_true")

    def handle(self, *args, **options):
        config_dir = options["config_dir"]
        self.stdout.write(f"[import_plain_config] config-dir: {config_dir}")
        if options["clear"]:
            SubmissionFormField.objects.all().delete()
            SubmissionForm.objects.all().delete()
            MetadataField.objects.all().delete()
            MetadataSchema.objects.all().delete()
            self.stdout.write("Cleared all existing records.")
        if not options["skip_metadata"]:
            self._import_metadata(config_dir)
        if not options["skip_forms"]:
            self._import_forms(config_dir)

    # ── Metadata registry ─────────────────────────────────────────────────────

    def _import_metadata(self, config_dir: str):
        path = os.path.join(config_dir, "metadata-registry-config.ts")
        if not os.path.exists(path):
            self.stderr.write(f"Not found: {path}"); return

        with open(path, encoding="utf-8-sig") as f:
            raw = f.read()

        # Restrict to METADATA_SCHEMAS section only (avoid flat METADATA_FIELDS array)
        schemas_start = raw.find("export const METADATA_SCHEMAS")
        fields_export = raw.find("export const METADATA_FIELDS", schemas_start + 10)
        raw_schemas = raw[schemas_start : fields_export if fields_export > 0 else len(raw)]

        schema_meta: dict[str, dict] = {}
        field_rows:  dict[str, dict] = {}   # keyed by unique FQN

        # For each field object in the section: extract the COMPLETE {} block using
        # brace-matching so qualifier is read only from the current field's own object.
        for fm in re.finditer(
            r'(?<!\w)\{\s*\n?\s*schema:\s*"([^"]+)",\s*\n?\s*element:\s*"([^"]+)"',
            raw_schemas
        ):
            schema_name = fm.group(1)
            element     = fm.group(2)

            # Brace-matched extraction — stops at the closing } of THIS field object
            obj = self._extract_obj(raw_schemas, fm.start())

            qualifier  = self._sv(obj, "qualifier") or ""
            field_fqn  = self._sv(obj, "field") or ""
            scope_note = self._sv(obj, "scopeNote") or ""
            source     = self._sv(obj, "source") or ""

            if not field_fqn:
                field_fqn = schema_name + "." + element
                if qualifier:
                    field_fqn += "." + qualifier

            if schema_name not in schema_meta:
                schema_meta[schema_name] = {
                    "namespace": "",
                    "title":     "",
                    "source":    source,
                }

            # First occurrence of a FQN wins — no subsequent overwrites
            if field_fqn not in field_rows:
                field_rows[field_fqn] = {
                    "schema_name": schema_name,
                    "element":     element,
                    "qualifier":   qualifier,
                    "scope_note":  scope_note,
                    "source":      source,
                }

        self.stdout.write(
            f"Collected {len(schema_meta)} schemas, {len(field_rows)} unique fields."
        )

        # Upsert schemas
        schema_objs: dict[str, MetadataSchema] = {}
        with transaction.atomic():
            for name, meta in schema_meta.items():
                obj, _ = MetadataSchema.objects.update_or_create(
                    name=name, defaults=meta,
                )
                schema_objs[name] = obj

        # Upsert fields — keyed on unique FQN column, no duplicate (schema,element,qualifier)
        field_count = 0
        with transaction.atomic():
            for field_fqn, row in field_rows.items():
                schema_obj = schema_objs.get(row["schema_name"])
                if not schema_obj:
                    schema_obj, _ = MetadataSchema.objects.get_or_create(
                        name=row["schema_name"],
                        defaults={"source": row["source"]},
                    )
                    schema_objs[row["schema_name"]] = schema_obj

                MetadataField.objects.update_or_create(
                    field=field_fqn,
                    defaults={
                        "schema":     schema_obj,
                        "element":    row["element"],
                        "qualifier":  row["qualifier"],
                        "scope_note": row["scope_note"],
                        "source":     row["source"],
                    },
                )
                field_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Metadata: {len(schema_objs)} schemas, {field_count} fields imported."
        ))

    # ── Submission forms ──────────────────────────────────────────────────────

    def _import_forms(self, config_dir: str):
        path = os.path.join(config_dir, "submission-config.ts")
        if not os.path.exists(path):
            self.stderr.write(f"Not found: {path}"); return

        with open(path, encoding="utf-8-sig") as f:
            raw = f.read()

        # Only scan SUBMISSION_PROCESSES section to avoid double-counting edit forms
        proc_start = raw.find("export const SUBMISSION_PROCESSES")
        raw_forms = raw[proc_start:] if proc_start >= 0 else raw

        forms: dict[str, dict] = {}
        pos = 0
        while True:
            m = re.search(r'name:\s*"([^"]+)",\s*\n?\s*rows:\s*\[', raw_forms[pos:])
            if not m: break
            name = m.group(1)
            abs_start = pos + m.start()
            rows_str, _ = self._bracket(raw_forms, pos + m.end() - 1, "[", "]")
            if name not in forms:
                rows = self._parse_rows(rows_str)
                cr = re.search(r'containsRequiredFields:\s*(true|false)',
                               raw_forms[abs_start:abs_start + 200])
                forms[name] = {
                    "rows": rows,
                    "containsRequired": (cr.group(1) == "true") if cr else False,
                }
            pos = abs_start + 1

        self.stdout.write(f"Forms collected: {len(forms)}")

        with transaction.atomic():
            form_objs: dict[str, SubmissionForm] = {}
            for name, fdata in forms.items():
                obj, _ = SubmissionForm.objects.update_or_create(
                    name=name,
                    defaults={"contains_required": fdata["containsRequired"]},
                )
                form_objs[name] = obj

            field_count = 0
            for name, fdata in forms.items():
                form_obj = form_objs[name]
                row_idx = 0
                for row in fdata["rows"]:
                    for col_idx, field in enumerate(row):
                        if not isinstance(field, dict): continue
                        child_name = field.get("childFormName") or ""
                        child_obj  = form_objs.get(child_name)
                        SubmissionFormField.objects.update_or_create(
                            form=form_obj, row=row_idx, col=col_idx,
                            defaults={
                                "field":             field.get("field") or "",
                                "label":             field.get("label") or "",
                                "input_type":        (field.get("inputType") or "onebox")[:20],
                                "is_required":       bool(field.get("isRequired")),
                                "required_msg":      field.get("required") or "",
                                "repeatable":        bool(field.get("repeatable")),
                                "vocabulary":        field.get("vocabulary") or "",
                                "vocabulary_closed": bool(field.get("vocabularyClosed")),
                                "value_pairs_name":  field.get("valuePairsName") or "",
                                "hint":              field.get("hint") or "",
                                "style":             field.get("style") or "",
                                "regex":             field.get("regex") or "",
                                "language_codes":    field.get("languageCodes") or [],
                                "type_binds":        field.get("typeBinds") or [],
                                "child_form_name":   child_name,
                                "child_form":        child_obj,
                            },
                        )
                        field_count += 1
                    row_idx += 1

        self.stdout.write(self.style.SUCCESS(
            f"Submission forms: {len(form_objs)} forms, {field_count} fields imported."
        ))

    # ── Parsing helpers ───────────────────────────────────────────────────────

    def _extract_obj(self, s: str, start: int) -> str:
        """Return the complete {...} object starting at start using brace matching."""
        depth = 0; i = start
        while i < len(s):
            if s[i] == '{':   depth += 1
            elif s[i] == '}':
                depth -= 1
                if depth == 0: return s[start:i+1]
            i += 1
        return s[start:]

    def _bracket(self, s, start, open_c, close_c):
        depth = 0; i = start
        while i < len(s):
            if s[i] == open_c:   depth += 1
            elif s[i] == close_c:
                depth -= 1
                if depth == 0: return s[start:i+1], i+1
            i += 1
        return s[start:], len(s)

    def _parse_rows(self, rows_str):
        rows = []
        i = 1
        while i < len(rows_str) - 1:
            if rows_str[i] == "[":
                row_str, end = self._bracket(rows_str, i, "[", "]")
                fields = []
                j = 1
                while j < len(row_str) - 1:
                    if row_str[j] == "{":
                        obj_str, eend = self._bracket(row_str, j, "{", "}")
                        f = self._parse_field(obj_str)
                        if f: fields.append(f)
                        j = eend
                    else: j += 1
                if fields: rows.append(fields)
                i = end
            else: i += 1
        return rows

    def _parse_field(self, obj_str):
        d = {}
        cf_m = re.search(r'\bchildForm\s*:\s*\{', obj_str)
        outer = obj_str
        if cf_m:
            cf_str = self._extract_obj(obj_str, cf_m.end() - 1)
            outer = obj_str[:cf_m.start()] + obj_str[cf_m.start() + len(cf_str) + 12:]
            cfn = re.search(r'name:\s*"([^"]+)"', cf_str)
            if cfn: d["childFormName"] = cfn.group(1)
        for key, val in re.findall(
            r'\b([a-zA-Z][a-zA-Z0-9_]*)\s*:\s*'
            r'("(?:[^"\\]|\\.)*"|true|false|null|-?[0-9]+(?:\.[0-9]+)?)',
            outer
        ):
            if key == "childForm": continue
            if val.startswith('"'): d[key] = val[1:-1].replace('\\"', '"')
            elif val == "true":  d[key] = True
            elif val == "false": d[key] = False
            elif val == "null":  d[key] = None
            else:
                try: d[key] = int(val)
                except: d[key] = val
        for key, arr in re.findall(r'\b([a-zA-Z][a-zA-Z0-9_]*)\s*:\s*(\[[^\]]*\])', outer):
            if key == "childForm": continue
            try:
                cleaned = re.sub(r"'([^']*)'", r'"\1"', arr)
                d[key] = json.loads(re.sub(r',\s*\]', ']', cleaned))
            except: d[key] = []
        return d or None

    def _sv(self, block, key):
        m = re.search(rf'\b{re.escape(key)}\s*:\s*"([^"]*)"', block)
        return m.group(1) if m else None
