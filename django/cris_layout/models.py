"""
cris_layout/models.py

Django models for the DSpace CRIS layout configuration.

Maps exactly to the 14 sheets in the cris-layout-configuration.xls:
  tab                   → CrisLayoutTab
  tab2box               → CrisLayoutTab2Box
  box                   → CrisLayoutBox
  box2metadata          → CrisLayoutBox2Metadata
  box2metrics           → CrisLayoutBox2Metrics
  box2hierarchicalvocabulary → CrisLayoutBox2Vocabulary
  metadatagroups        → CrisLayoutMetadataGroup
  tabpolicy             → CrisLayoutTabPolicy
  boxpolicy             → CrisLayoutBoxPolicy

i18n sheets are derived/auto-generated on export — not stored separately.
"""
from django.db import models


SECURITY_CHOICES = [
    ("PUBLIC",                  "Public"),
    ("ADMINISTRATOR",           "Administrator"),
    ("OWNER ONLY",              "Owner Only"),
    ("OWNER & ADMINISTRATOR",   "Owner & Administrator"),
    ("CUSTOM DATA",             "Custom Data"),
    ("CUSTOM DATA & ADMINISTRATOR", "Custom Data & Administrator"),
]

BOX_TYPE_CHOICES = [
    ("METADATA",    "Metadata"),
    ("RELATION",    "Relation"),
    ("METRICS",     "Metrics"),
    ("IIIFVIEWER",  "IIIF Viewer"),
    ("NETWORKLAB",  "Network Lab"),
    ("BITSTREAM",   "Bitstream"),
]

FIELDTYPE_CHOICES = [
    ("METADATA",      "Metadata"),
    ("BITSTREAM",     "Bitstream"),
    ("METADATAGROUP", "Metadata Group"),
]


class CrisLayoutTab(models.Model):
    """tab sheet — one row per entity tab."""
    entity    = models.CharField(max_length=100)
    shortname = models.CharField(max_length=200)
    label     = models.CharField(max_length=200, blank=True, default="")
    priority  = models.IntegerField(default=0)
    leading   = models.BooleanField(default=False, help_text="y/n — is this the leading (default) tab?")
    security  = models.CharField(max_length=60, choices=SECURITY_CHOICES, default="PUBLIC")

    class Meta:
        ordering = ["entity", "priority"]
        unique_together = [("entity", "shortname")]
        verbose_name = "Layout Tab"
        verbose_name_plural = "Layout Tabs"

    def __str__(self):
        return f"{self.entity} / {self.shortname}"


class CrisLayoutTab2Box(models.Model):
    """tab2box sheet — maps tabs to boxes with row positioning."""
    entity     = models.CharField(max_length=100)
    tab        = models.CharField(max_length=200)
    row        = models.FloatField(default=1)
    row_style  = models.CharField(max_length=200, blank=True, default="")
    cell_style = models.CharField(max_length=200, blank=True, default="")
    boxes      = models.CharField(max_length=500, help_text="Comma-separated box shortnames")

    class Meta:
        ordering = ["entity", "tab", "row"]
        verbose_name = "Tab → Box Mapping"
        verbose_name_plural = "Tab → Box Mappings"

    def __str__(self):
        return f"{self.entity} / {self.tab} row {self.row} → {self.boxes}"

    @property
    def box_list(self):
        return [b.strip() for b in self.boxes.split(",") if b.strip()]


class CrisLayoutBox(models.Model):
    """box sheet — defines each box."""
    entity    = models.CharField(max_length=100)
    shortname = models.CharField(max_length=200)
    label     = models.CharField(max_length=200, blank=True, default="")
    box_type  = models.CharField(max_length=20, choices=BOX_TYPE_CHOICES, default="METADATA",
                                  db_column="type")
    collapsed = models.BooleanField(default=False)
    container = models.BooleanField(default=True)
    minor     = models.BooleanField(default=False)
    security  = models.CharField(max_length=60, choices=SECURITY_CHOICES, default="PUBLIC")
    style     = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        ordering = ["entity", "shortname"]
        unique_together = [("entity", "shortname")]
        verbose_name = "Layout Box"
        verbose_name_plural = "Layout Boxes"

    def __str__(self):
        return f"{self.entity} / {self.shortname} ({self.box_type})"


class CrisLayoutBox2Metadata(models.Model):
    """box2metadata sheet — fields inside boxes."""
    entity          = models.CharField(max_length=100)
    box             = models.CharField(max_length=200)
    row             = models.FloatField(default=1)
    cell            = models.FloatField(default=1)
    field_type      = models.CharField(max_length=20, choices=FIELDTYPE_CHOICES, default="METADATA",
                                        db_column="fieldtype")
    metadata        = models.CharField(max_length=400, blank=True, default="")
    value           = models.CharField(max_length=400, blank=True, default="",
                                        help_text="Fixed value / dc.type filter for BITSTREAMs")
    bundle          = models.CharField(max_length=200, blank=True, default="")
    label           = models.CharField(max_length=500, blank=True, default="")
    label_as_heading = models.BooleanField(default=False)
    rendering       = models.CharField(max_length=200, blank=True, default="")
    values_inline   = models.BooleanField(default=False)
    row_style       = models.CharField(max_length=200, blank=True, default="")
    cell_style      = models.CharField(max_length=200, blank=True, default="")
    style_label     = models.CharField(max_length=200, blank=True, default="")
    style_value     = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        ordering = ["entity", "box", "row", "cell"]
        verbose_name = "Box → Metadata Field"
        verbose_name_plural = "Box → Metadata Fields"

    def __str__(self):
        return f"{self.entity}/{self.box} [{self.row},{self.cell}] {self.metadata or self.field_type}"


class CrisLayoutBox2Metrics(models.Model):
    """box2metrics sheet — metric types attached to a box."""
    entity      = models.CharField(max_length=100)
    box         = models.CharField(max_length=200)
    metric_type = models.TextField(help_text="Comma-separated metric type identifiers")

    class Meta:
        ordering = ["entity", "box"]
        unique_together = [("entity", "box")]
        verbose_name = "Box → Metrics"
        verbose_name_plural = "Box → Metrics"

    def __str__(self):
        return f"{self.entity} / {self.box}: {self.metric_type[:60]}"

    @property
    def metric_list(self):
        return [m.strip() for m in self.metric_type.split(",") if m.strip()]


class CrisLayoutBox2Vocabulary(models.Model):
    """box2hierarchicalvocabulary sheet."""
    entity     = models.CharField(max_length=100)
    box        = models.CharField(max_length=200)
    vocabulary = models.CharField(max_length=200)
    metadata   = models.CharField(max_length=400, blank=True, default="")

    class Meta:
        ordering = ["entity", "box"]
        verbose_name = "Box → Hierarchical Vocabulary"
        verbose_name_plural = "Box → Hierarchical Vocabularies"

    def __str__(self):
        return f"{self.entity}/{self.box} → {self.vocabulary}"


class CrisLayoutMetadataGroup(models.Model):
    """metadatagroups sheet — child fields inside a METADATAGROUP."""
    entity      = models.CharField(max_length=100)
    parent      = models.CharField(max_length=400,
                                    help_text="Parent metadata field (the group key)")
    field_type  = models.CharField(max_length=20, choices=FIELDTYPE_CHOICES, default="METADATA",
                                    db_column="fieldtype")
    metadata    = models.CharField(max_length=400)
    value       = models.CharField(max_length=400, blank=True, default="")
    bundle      = models.CharField(max_length=200, blank=True, default="")
    label       = models.CharField(max_length=500, blank=True, default="")
    rendering   = models.CharField(max_length=200, blank=True, default="")
    style_label = models.CharField(max_length=200, blank=True, default="")
    style_value = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        ordering = ["entity", "parent", "id"]
        verbose_name = "Metadata Group Field"
        verbose_name_plural = "Metadata Group Fields"

    def __str__(self):
        return f"{self.entity} / {self.parent} → {self.metadata}"


class CrisLayoutTabPolicy(models.Model):
    """tabpolicy sheet — access policy rules for tabs."""
    entity    = models.CharField(max_length=100)
    shortname = models.CharField(max_length=200)
    metadata  = models.CharField(max_length=400)
    group     = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        ordering = ["entity", "shortname"]
        verbose_name = "Tab Policy"
        verbose_name_plural = "Tab Policies"

    def __str__(self):
        return f"{self.entity}/{self.shortname} → {self.metadata}"


class CrisLayoutBoxPolicy(models.Model):
    """boxpolicy sheet — access policy rules for boxes."""
    entity    = models.CharField(max_length=100)
    shortname = models.CharField(max_length=200)
    metadata  = models.CharField(max_length=400)
    group     = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        ordering = ["entity", "shortname"]
        verbose_name = "Box Policy"
        verbose_name_plural = "Box Policies"

    def __str__(self):
        return f"{self.entity}/{self.shortname} → {self.metadata}"
