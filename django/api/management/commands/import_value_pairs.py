"""
Management command: import_value_pairs

Parses the <form-value-pairs> section of DSpace submission-forms.xml and
populates the SubmissionValuePairSet / SubmissionValuePair database tables.

This command is idempotent — running it multiple times is safe.  It uses
update_or_create for sets and replaces pairs atomically per set.

Usage
-----
    python manage.py import_value_pairs
    python manage.py import_value_pairs --file /dspace/config/submission-forms.xml
    python manage.py import_value_pairs --clear   # wipe all value pairs first
"""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from api.models import SubmissionValuePairSet, SubmissionValuePair


DEFAULT_PATHS = [
    "/dspace/config/submission-forms.xml",
    "/app/config/submission-forms.xml",
    os.path.join(settings.BASE_DIR, "config", "submission-forms.xml"),
]


def find_xml() -> str | None:
    for p in DEFAULT_PATHS:
        if Path(p).exists():
            return p
    return None


def parse_value_pairs(xml_path: str) -> list[dict]:
    """
    Parse <form-value-pairs> from submission-forms.xml.
    Returns list of dicts:
      {"name": str, "dc_term": str, "pairs": [{"displayed_value": str, "stored_value": str}]}
    """
    try:
        tree = ET.parse(xml_path)
    except ET.ParseError as e:
        raise CommandError(f"XML parse error in {xml_path}: {e}")

    root = tree.getroot()

    # Handle both root <input-forms> and direct <form-value-pairs>
    fvp = root.find("form-value-pairs")
    if fvp is None and root.tag == "form-value-pairs":
        fvp = root
    if fvp is None:
        return []

    result = []
    for vps_el in fvp.findall("value-pairs"):
        name    = vps_el.get("value-pairs-name", "").strip()
        dc_term = vps_el.get("dc-term", "").strip()
        if not name:
            continue
        pairs = []
        for pair_el in vps_el.findall("pair"):
            dv = (pair_el.findtext("displayed-value") or "").strip()
            sv = (pair_el.findtext("stored-value")    or "").strip()
            pairs.append({"displayed_value": dv, "stored_value": sv})
        result.append({"name": name, "dc_term": dc_term, "pairs": pairs})
    return result


class Command(BaseCommand):
    help = "Import DSpace submission form value-pair sets from submission-forms.xml"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file", default="",
            help="Path to submission-forms.xml (auto-detected if omitted)",
        )
        parser.add_argument(
            "--clear", action="store_true",
            help="Delete all existing value-pair sets before importing",
        )

    def handle(self, *args, **options):
        xml_path = options["file"] or find_xml()
        if not xml_path:
            raise CommandError(
                "Could not find submission-forms.xml. "
                "Pass --file /path/to/submission-forms.xml"
            )
        if not Path(xml_path).exists():
            raise CommandError(f"File not found: {xml_path}")

        self.stdout.write(f"Parsing: {xml_path}")
        sets = parse_value_pairs(xml_path)

        if not sets:
            self.stdout.write(self.style.WARNING(
                "No <form-value-pairs> section found in the file. Nothing imported."
            ))
            return

        with transaction.atomic():
            if options["clear"]:
                self.stdout.write(self.style.WARNING("Clearing all value-pair sets…"))
                SubmissionValuePairSet.objects.all().delete()

            created_sets = updated_sets = total_pairs = 0

            for data in sets:
                vps, created = SubmissionValuePairSet.objects.update_or_create(
                    name=data["name"],
                    defaults={"dc_term": data["dc_term"]},
                )
                if created:
                    created_sets += 1
                else:
                    updated_sets += 1
                    vps.pairs.all().delete()  # replace pairs on re-import

                for i, pair in enumerate(data["pairs"]):
                    SubmissionValuePair.objects.create(
                        pair_set=vps,
                        sort_order=i,
                        displayed_value=pair["displayed_value"],
                        stored_value=pair["stored_value"],
                    )
                    total_pairs += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done: {created_sets} sets created, {updated_sets} sets updated, "
            f"{total_pairs} pairs imported across {len(sets)} sets."
        ))
        for data in sets:
            self.stdout.write(f"  {data['name']}: {len(data['pairs'])} pairs")
