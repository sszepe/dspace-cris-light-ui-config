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


# ── Collection mapping ────────────────────────────────────────────────────────
#
# Mirrors the STATIC_COLLECTION_RULES array in collection-mapping.ts.
# Rules are evaluated in sort_order; the first matching rule wins.

class CollectionMapping(models.Model):
    entity_type   = models.CharField(max_length=200,
                                      help_text="DSpace entity type, e.g. 'Funding', 'OrgUnit'")
    collection_id = models.CharField(max_length=200,
                                      help_text="Target DSpace collection UUID")
    label         = models.CharField(max_length=300, blank=True, default="",
                                      help_text="Human-readable description shown in admin UI")
    # Conditions (stored as JSON; null means 'match all')
    dc_type_includes      = models.JSONField(
        default=list, blank=True,
        help_text="dc.type must contain any of these strings (case-insensitive)")
    risfunding_status_in  = models.JSONField(
        default=list, blank=True,
        help_text="risfunding.status must equal one of these values")
    sort_order    = models.PositiveIntegerField(default=0,
                                                help_text="Rules are evaluated in ascending order; first match wins")
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering     = ["sort_order", "entity_type"]
        verbose_name = "Collection Mapping"
        verbose_name_plural = "Collection Mappings"

    def __str__(self):
        conds = []
        if self.dc_type_includes:
            conds.append(f"dc.type∈{self.dc_type_includes}")
        if self.risfunding_status_in:
            conds.append(f"status∈{self.risfunding_status_in}")
        suffix = f" [{', '.join(conds)}]" if conds else ""
        return f"{self.entity_type} → {self.collection_id}{suffix}"


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


# ── Submission processes ──────────────────────────────────────────────────────
#
# Mirrors item-submission.xml:
#   <step-definitions>  → SubmissionStepDefinition (read-only, imported)
#   <submission-definitions>/<submission-process>  → SubmissionProcess + SubmissionProcessStep

class SubmissionStepDefinition(models.Model):
    """One <step-definition> from item-submission.xml."""
    SCOPE_CHOICES = [
        ("submission", "Submission"),
        ("workflow",   "Workflow"),
        ("both",       "Both"),
    ]
    step_id          = models.CharField(max_length=200, unique=True,
                                         help_text="The @id attribute, e.g. 'publication'")
    heading          = models.CharField(max_length=500, blank=True, default="",
                                         help_text="i18n key, e.g. submit.progressbar.describe.publication")
    processing_class = models.CharField(max_length=500, blank=True, default="")
    type             = models.CharField(max_length=100, blank=True, default="",
                                         help_text="step type, e.g. submission-form, upload, license")
    mandatory        = models.BooleanField(default=True)
    scope            = models.CharField(max_length=20, choices=SCOPE_CHOICES,
                                         blank=True, default="",
                                         help_text="Scope visibility restriction if any")
    imported_at      = models.DateTimeField(auto_now=True)

    class Meta:
        ordering       = ["step_id"]
        verbose_name   = "Step Definition"
        verbose_name_plural = "Step Definitions"

    def __str__(self):
        return self.step_id


class SubmissionProcess(models.Model):
    """One <submission-process> from item-submission.xml."""
    name        = models.CharField(max_length=200, unique=True,
                                    help_text="The @name attribute, e.g. 'publication'")
    imported_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering       = ["name"]
        verbose_name   = "Submission Process"
        verbose_name_plural = "Submission Processes"

    def __str__(self):
        return self.name

    @property
    def step_count(self):
        return self.steps.count()


class SubmissionProcessStep(models.Model):
    """One <step id="…"/> inside a <submission-process>."""
    process    = models.ForeignKey(SubmissionProcess, on_delete=models.CASCADE,
                                    related_name="steps")
    sort_order = models.PositiveIntegerField(default=0)
    step_id    = models.CharField(max_length=200,
                                   help_text="References SubmissionStepDefinition.step_id")
    # Resolved FK — null if the step_id is not in step-definitions (e.g. detect-duplicate)
    definition = models.ForeignKey(SubmissionStepDefinition, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="process_steps")

    class Meta:
        ordering       = ["sort_order"]
        unique_together = [("process", "sort_order")]

    def __str__(self):
        return f"{self.process.name}[{self.sort_order}] → {self.step_id}"


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

# ── Key Value pairs ────────────────────────────────────────────────────────────

class SubmissionValuePairSet(models.Model):
    """
    A named set of key/value pairs used by dropdown and qualdrop_value fields
    in DSpace submission forms (e.g. common_iso_languages, gender, orgunit_types).

    Maps to <value-pairs value-pairs-name="..." dc-term="..."> in submission-forms.xml
    and to an entry in SUBMISSION_VALUE_PAIRS in submission-value-pairs.tsx.
    """
    name     = models.CharField(max_length=200, unique=True,
                                help_text='Value pairs name (e.g. "common_iso_languages")')
    dc_term  = models.CharField(max_length=200, blank=True,
                                help_text='dc-term attribute from submission-forms.xml')
    note     = models.TextField(blank=True, help_text="Optional description / notes")
    imported_at = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Submission value-pair set"
        verbose_name_plural = "Submission value-pair sets"

    def __str__(self):
        return self.name


class SubmissionValuePair(models.Model):
    """
    A single displayed-value / stored-value pair within a SubmissionValuePairSet.
    Maps to <pair><displayed-value>…</displayed-value><stored-value>…</stored-value></pair>.
    """
    pair_set       = models.ForeignKey(
        SubmissionValuePairSet, on_delete=models.CASCADE, related_name="pairs"
    )
    sort_order     = models.PositiveIntegerField(default=0)
    displayed_value = models.CharField(max_length=500)
    stored_value   = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Submission value pair"
        verbose_name_plural = "Submission value pairs"

    def __str__(self):
        return f"{self.pair_set.name}: {self.displayed_value} → {self.stored_value}"