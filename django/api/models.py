from django.db import models


# ── Dashboard clusters ────────────────────────────────────────────────────────

class EntityCluster(models.Model):
    key         = models.CharField(max_length=100, unique=True)
    label       = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    sort_order  = models.PositiveIntegerField(default=0)
    enabled     = models.BooleanField(default=True)
    class Meta: ordering = ["sort_order", "label"]
    def __str__(self): return self.label

class EntityTypeEntry(models.Model):
    cluster           = models.ForeignKey(EntityCluster, on_delete=models.CASCADE, related_name="entity_types")
    entity_type_label = models.CharField(max_length=200)
    sort_order        = models.PositiveIntegerField(default=0)
    class Meta: ordering = ["sort_order"]
    def __str__(self): return f"{self.cluster.key} → {self.entity_type_label}"


# ── Quicklinks ────────────────────────────────────────────────────────────────

class QuickPreset(models.Model):
    key          = models.CharField(max_length=100, unique=True)
    label        = models.CharField(max_length=200)
    description  = models.TextField(blank=True, default="")
    base_filters = models.JSONField(default=dict)
    sort_order   = models.PositiveIntegerField(default=0)
    enabled      = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
    class Meta: ordering = ["sort_order", "label"]
    def __str__(self): return self.label

class QuickPresetFilter(models.Model):
    KIND_CHOICES = [("text", "Text"), ("date", "Date")]
    preset      = models.ForeignKey(QuickPreset, on_delete=models.CASCADE, related_name="filters")
    key         = models.CharField(max_length=100)
    label       = models.CharField(max_length=200)
    facet_name  = models.CharField(max_length=200)
    kind        = models.CharField(max_length=10, choices=KIND_CHOICES, default="text")
    placeholder = models.CharField(max_length=200, blank=True, default="")
    sort_order  = models.PositiveIntegerField(default=0)
    class Meta: ordering = ["sort_order"]
    def __str__(self): return f"{self.preset.key} / {self.key}"


# ── Site settings ─────────────────────────────────────────────────────────────

class SiteSettings(models.Model):
    quicklinks_enabled                  = models.BooleanField(default=True)
    communities_creation_enabled        = models.BooleanField(default=True)
    communities_role_management_enabled = models.BooleanField(default=True)
    collections_creation_enabled        = models.BooleanField(default=True)
    updated_at                          = models.DateTimeField(auto_now=True)
    class Meta: verbose_name = verbose_name_plural = "Site Settings"
    def __str__(self): return "Site Settings"
    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


# ── Metadata registry ─────────────────────────────────────────────────────────

class MetadataSchema(models.Model):
    name      = models.CharField(max_length=100, unique=True)
    namespace = models.CharField(max_length=500, blank=True, default="")
    title     = models.CharField(max_length=200, blank=True, default="")
    source    = models.CharField(max_length=200, blank=True, default="",
                                  help_text="Source XML file, e.g. dc-types.xml")
    class Meta: ordering = ["name"]
    def __str__(self): return self.name

class MetadataField(models.Model):
    schema     = models.ForeignKey(MetadataSchema, on_delete=models.CASCADE, related_name="fields")
    element    = models.CharField(max_length=200)
    qualifier  = models.CharField(max_length=200, blank=True, default="")
    field      = models.CharField(max_length=400, unique=True,
                                   help_text="Dotted field name, e.g. dc.title.alternative")
    scope_note = models.TextField(blank=True, default="")
    source     = models.CharField(max_length=200, blank=True, default="")
    class Meta:
        ordering = ["field"]
        unique_together = [("schema", "element", "qualifier")]
    def __str__(self): return self.field


# ── Submission forms ──────────────────────────────────────────────────────────

class SubmissionForm(models.Model):
    name             = models.CharField(max_length=200, unique=True)
    contains_required = models.BooleanField(default=False)
    imported_at      = models.DateTimeField(auto_now=True)
    class Meta: ordering = ["name"]
    def __str__(self): return self.name

class SubmissionFormField(models.Model):
    INPUT_TYPES = [
        ("onebox","One box"),("textarea","Textarea"),("twobox","Two box"),
        ("name","Name"),("date","Date"),("series","Series"),
        ("dropdown","Dropdown"),("list","List"),("lookup","Lookup"),
        ("lookup-name","Lookup Name"),("tag","Tag"),
        ("qualdrop_value","Qualdrop"),("group","Group"),
        ("inline-group","Inline Group"),("link","Link"),
    ]
    form             = models.ForeignKey(SubmissionForm, on_delete=models.CASCADE, related_name="fields")
    row              = models.PositiveIntegerField(default=0)
    col              = models.PositiveIntegerField(default=0)
    field            = models.CharField(max_length=400, blank=True, default="")
    label            = models.CharField(max_length=500, blank=True, default="")
    input_type       = models.CharField(max_length=20, choices=INPUT_TYPES, default="onebox")
    is_required      = models.BooleanField(default=False)
    required_msg     = models.CharField(max_length=500, blank=True, default="")
    repeatable       = models.BooleanField(default=False)
    vocabulary       = models.CharField(max_length=200, blank=True, default="")
    vocabulary_closed = models.BooleanField(default=False)
    value_pairs_name = models.CharField(max_length=200, blank=True, default="")
    hint             = models.TextField(blank=True, default="")
    style            = models.CharField(max_length=200, blank=True, default="")
    regex            = models.CharField(max_length=500, blank=True, default="")
    language_codes   = models.JSONField(default=list,
                                         help_text="List of allowed language codes, e.g. ['en','de']")
    type_binds       = models.JSONField(default=list,
                                        help_text="dc.type values that reveal this field")
    # Group field support
    child_form_name  = models.CharField(max_length=200, blank=True, default="",
                                         help_text="For group/inline-group fields: name of the child form")
    child_form       = models.ForeignKey("SubmissionForm", null=True, blank=True,
                                          on_delete=models.SET_NULL, related_name="parent_fields",
                                          help_text="Resolved child form for group fields")
    class Meta: ordering = ["row", "col"]
    def __str__(self): return f"{self.form.name}[{self.row},{self.col}] {self.field or self.input_type}"


# ── Form layout overrides ─────────────────────────────────────────────────────

class FormLayout(models.Model):
    form_name  = models.CharField(max_length=200)
    profile    = models.CharField(max_length=100, blank=True, default="plain")
    collection = models.UUIDField(null=True, blank=True)
    label      = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["form_name", "profile"]
        unique_together = [("form_name", "profile", "collection")]
    def __str__(self): return f"{self.form_name} / {self.profile}"

class FormSection(models.Model):
    layout               = models.ForeignKey(FormLayout, on_delete=models.CASCADE, related_name="sections")
    key                  = models.CharField(max_length=100)
    label                = models.CharField(max_length=200)
    sort_order           = models.PositiveIntegerField(default=0)
    collapsed_by_default = models.BooleanField(default=False)
    helper_text_above    = models.TextField(blank=True, default="")
    helper_text_below    = models.TextField(blank=True, default="")
    class Meta: ordering = ["sort_order"]

class FormFieldOverride(models.Model):
    section        = models.ForeignKey(FormSection, on_delete=models.CASCADE, related_name="field_overrides")
    field_name     = models.CharField(max_length=400)
    sort_order     = models.PositiveIntegerField(default=0)
    label_override = models.CharField(max_length=500, blank=True, default="")
    hint_override  = models.TextField(blank=True, default="")
    hidden         = models.BooleanField(default=False)
    class Meta: ordering = ["sort_order"]

class FormConditionalBlock(models.Model):
    layout           = models.ForeignKey(FormLayout, on_delete=models.CASCADE, related_name="conditional_blocks")
    sort_order       = models.PositiveIntegerField(default=0)
    trigger_field    = models.CharField(max_length=400)
    trigger_value    = models.CharField(max_length=200)
    revealed_fields  = models.JSONField(default=list)
    revealed_section = models.CharField(max_length=100, blank=True, default="")
    class Meta: ordering = ["sort_order"]
