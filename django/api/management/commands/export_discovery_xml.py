"""
Management command: export_discovery_xml

Reads the base discovery.xml (DISCOVERY_XML_BASE setting or --base-file),
then for every facet_name used across QuickPreset filters:

  1.  If a bean with matching indexFieldName already exists → use it.
  2.  If not → auto-generate a DiscoverySearchFilterFacet bean and insert
      it before </beans>.
  3.  Ensure each resolved bean_id is referenced inside the
      defaultConfiguration sidebar and searchFilters <list> blocks.

The result is written to --output-file (default: discovery.xml) or stdout.

Typical setup
-------------
In settings/local.py:
    DISCOVERY_XML_BASE = "/app/dspace-config/discovery.xml"

Then the Django healthcheck / cockpit can call:
    python manage.py export_discovery_xml --output-file /path/to/patched.xml

Or via the cockpit's "⬇ discovery.xml" button which calls the view that
runs this command in a temp file and streams the result.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from django.core.management.base import BaseCommand

from api.models import QuickPresetFilter


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_field_to_bean_map(xml: str) -> dict[str, str]:
    """
    Scan the XML for <bean id="X"> … <property name="indexFieldName" value="Y">
    Returns { field_value: bean_id } (first occurrence wins).
    """
    mapping: dict[str, str] = {}
    for m in re.finditer(
        r'<bean\s+id="(searchFilter[^"]+)"[^>]*>.*?'
        r'<property\s+name="indexFieldName"\s+value="([^"]+)"',
        xml, re.DOTALL,
    ):
        bean_id, field = m.group(1), m.group(2)
        if field not in mapping:
            mapping[field] = bean_id
    return mapping


def _derive_bean_id(facet_name: str) -> str:
    """
    Derive a CamelCase bean id from a dotted facet_name.
    e.g. crispj.investigator → searchFilterCrispjInvestigator
         oairecerif.project.startDate → searchFilterOairerecerifProjectStartDate
    """
    parts = re.split(r"[.\-_]", facet_name)
    camel = "".join(p[:1].upper() + p[1:] for p in parts if p)
    return f"searchFilter{camel}"


def _generate_bean(bean_id: str, facet_name: str, is_date: bool) -> str:
    """Return a minimal DiscoverySearchFilterFacet XML bean block."""
    bean_class = "org.dspace.discovery.configuration.DiscoverySearchFilterFacet"
    type_line = '\n        <property name="type" value="date"/>' if is_date else ""
    expose = "true" if is_date else "false"
    return (
        f'\n    <bean id="{bean_id}" class="{bean_class}">'
        f'\n        <property name="indexFieldName" value="{facet_name}"/>'
        f"{type_line}"
        f'\n        <property name="metadataFields">'
        f"\n            <list>"
        f"\n                <value>{facet_name}</value>"
        f"\n            </list>"
        f"\n        </property>"
        f'\n        <property name="facetLimit" value="5"/>'
        f'\n        <property name="sortOrderSidebar" value="COUNT"/>'
        f'\n        <property name="sortOrderFilterPage" value="COUNT"/>'
        f'\n        <property name="isOpenByDefault" value="false"/>'
        f'\n        <property name="pageSize" value="10"/>'
        f'\n        <property name="exposeMinAndMaxValue" value="{expose}"/>'
        f"\n    </bean>\n"
    )


def _already_referenced(xml: str, bean_id: str) -> bool:
    return bool(re.search(
        rf'<ref\s+bean=["\']?{re.escape(bean_id)}["\']?\s*/?>',
        xml,
    ))


def _insert_ref_before_list_close(block: str, prop_name: str, bean_id: str) -> str:
    """
    Within `block`, find <property name="{prop_name}"> … <list> … </list>
    and insert <ref bean="{bean_id}"/> just before the closing </list>.
    Only inserts once (the first matching list).
    """
    ref_line = f'                <ref bean="{bean_id}"/>\n'
    prop_pos = block.find(f'name="{prop_name}"')
    if prop_pos == -1:
        return block
    list_open = block.find("<list>", prop_pos)
    if list_open == -1:
        return block
    list_close = block.find("</list>", list_open)
    if list_close == -1:
        return block
    return block[:list_close] + ref_line + block[list_close:]


# ── Command ───────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = (
        "Patch discovery.xml with facet beans for every QuickPreset filter "
        "and ensure they are referenced in defaultConfiguration."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-file", default="",
            help=(
                "Path to the base discovery.xml. Falls back to the "
                "DISCOVERY_XML_BASE Django setting."
            ),
        )
        parser.add_argument(
            "--output-file", default="discovery.xml",
            help="Where to write the patched XML (default: discovery.xml).",
        )
        parser.add_argument(
            "--stdout", action="store_true",
            help="Write XML to stdout instead of a file.",
        )

    def handle(self, *args, **options):
        # ── Locate base file ──────────────────────────────────────────────────
        base_file = options["base_file"]
        if not base_file:
            from django.conf import settings
            base_file = getattr(settings, "DISCOVERY_XML_BASE", "")
        if not base_file or not Path(base_file).exists():
            self.stderr.write(self.style.ERROR(
                f"Base discovery.xml not found: '{base_file}'. "
                "Set DISCOVERY_XML_BASE in settings.py or use --base-file."
            ))
            sys.exit(1)

        xml = Path(base_file).read_text(encoding="utf-8")
        self.stdout.write(f"Base: {base_file} ({len(xml):,} chars)")

        # ── Collect facet_names from DB ───────────────────────────────────────
        facet_names: list[str] = sorted(set(
            QuickPresetFilter.objects
            .exclude(facet_name="")
            .values_list("facet_name", flat=True)
        ))
        if not facet_names:
            self.stdout.write(self.style.WARNING("No facet_names in DB — nothing to patch."))
        else:
            self.stdout.write(f"Facets to ensure: {facet_names}")

        # ── Build existing field → bean mapping ───────────────────────────────
        field_to_bean = _build_field_to_bean_map(xml)
        existing_bean_ids = set(field_to_bean.values())

        # ── Ensure every facet has a bean ─────────────────────────────────────
        new_bean_blocks: list[str] = []
        for facet_name in facet_names:
            if facet_name in field_to_bean:
                bid = field_to_bean[facet_name]
                self.stdout.write(f"  ✓ {facet_name} → {bid}")
                continue

            # Generate a unique bean_id
            base_id = _derive_bean_id(facet_name)
            bean_id = base_id
            suffix = 1
            while bean_id in existing_bean_ids:
                bean_id = f"{base_id}{suffix}"
                suffix += 1

            is_date = bool(re.search(r"[Dd]ate$", facet_name))
            new_bean_blocks.append(_generate_bean(bean_id, facet_name, is_date))
            field_to_bean[facet_name] = bean_id
            existing_bean_ids.add(bean_id)
            self.stdout.write(self.style.WARNING(f"  + new bean: {facet_name} → {bean_id}"))

        if new_bean_blocks:
            insert_block = (
                "\n    <!-- Auto-generated by export_discovery_xml -->\n"
                + "".join(new_bean_blocks)
            )
            xml = xml.replace("</beans>", insert_block + "</beans>", 1)

        # ── Ensure refs exist in defaultConfiguration ─────────────────────────
        dc_start = xml.find('<bean id="defaultConfiguration"')
        if dc_start == -1:
            self.stderr.write(self.style.WARNING(
                "defaultConfiguration bean not found — skipping ref injection."
            ))
        else:
            # Isolate the defaultConfiguration bean block
            # (ends at the next top-level </bean> at column 4)
            dc_end_match = re.search(r"\n    </bean>", xml[dc_start:])
            dc_end = dc_start + dc_end_match.start() if dc_end_match else len(xml)
            dc_block = xml[dc_start:dc_end]

            for facet_name in facet_names:
                bean_id = field_to_bean.get(facet_name)
                if not bean_id:
                    continue
                if _already_referenced(dc_block, bean_id):
                    continue
                # Add to both sidebar and searchFilters lists
                dc_block = _insert_ref_before_list_close(dc_block, "sidebar", bean_id)
                dc_block = _insert_ref_before_list_close(dc_block, "searchFilters", bean_id)
                self.stdout.write(f"  + ref: {bean_id} → defaultConfiguration")

            xml = xml[:dc_start] + dc_block + xml[dc_end:]

        # ── Write output ──────────────────────────────────────────────────────
        if options["stdout"]:
            sys.stdout.write(xml)
        else:
            out = Path(options["output_file"])
            out.write_text(xml, encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(
                f"Written → {out} ({len(xml):,} chars, "
                f"{xml.count(chr(10))+1} lines)"
            ))
