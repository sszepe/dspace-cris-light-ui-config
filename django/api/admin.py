from django.contrib import admin
from .models import (
    EntityCluster, EntityTypeEntry,
    QuickPreset, QuickPresetFilter,
    SiteSettings,
    CollectionMapping,
    MetadataSchema, MetadataField,
    SubmissionForm, SubmissionFormField,
    SubmissionStepDefinition, SubmissionProcess, SubmissionProcessStep,
    FormLayout, FormSection, FormFieldOverride, FormConditionalBlock,
)


# ── Entity clusters ───────────────────────────────────────────────────────────

class EntityTypeEntryInline(admin.TabularInline):
    model    = EntityTypeEntry
    extra    = 1
    fields   = ["entity_type_label", "sort_order"]
    ordering = ["sort_order"]

@admin.register(EntityCluster)
class EntityClusterAdmin(admin.ModelAdmin):
    list_display  = ["key", "label", "sort_order", "enabled"]
    list_editable = ["sort_order", "enabled"]
    inlines       = [EntityTypeEntryInline]


# ── Quicklinks ────────────────────────────────────────────────────────────────

class QuickPresetFilterInline(admin.TabularInline):
    model    = QuickPresetFilter
    extra    = 1
    fields   = ["key", "label", "facet_name", "kind", "placeholder", "sort_order"]
    ordering = ["sort_order"]

@admin.register(QuickPreset)
class QuickPresetAdmin(admin.ModelAdmin):
    list_display  = ["key", "label", "sort_order", "enabled", "updated_at"]
    list_editable = ["sort_order", "enabled"]
    inlines       = [QuickPresetFilterInline]


# ── Site settings (singleton) ─────────────────────────────────────────────────

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = [
        "quicklinks_enabled",
        "communities_creation_enabled",
        "communities_role_management_enabled",
        "collections_creation_enabled",
        "updated_at",
    ]
    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()
    def has_delete_permission(self, request, obj=None):
        return False


# ── Collection mapping ────────────────────────────────────────────────────────

@admin.register(CollectionMapping)
class CollectionMappingAdmin(admin.ModelAdmin):
    list_display  = ["entity_type", "sort_order", "collection_id", "label",
                     "dc_type_includes", "risfunding_status_in", "updated_at"]
    list_editable = ["sort_order"]
    list_filter   = ["entity_type"]
    search_fields = ["entity_type", "collection_id", "label"]
    ordering      = ["sort_order", "entity_type"]
    fieldsets     = [
        (None, {
            "fields": ["entity_type", "collection_id", "label", "sort_order"],
        }),
        ("Conditions (leave blank to match all)", {
            "fields": ["dc_type_includes", "risfunding_status_in"],
            "description": (
                "dc_type_includes: JSON list of dc.type substrings, e.g. [\"Grant\", \"Scholarship\"]. "
                "risfunding_status_in: JSON list of exact statuses, e.g. [\"approved\"]."
            ),
        }),
    ]


# ── Metadata registry (read-only in admin — imported via management command) ──

class MetadataFieldInline(admin.TabularInline):
    model           = MetadataField
    extra           = 0
    fields          = ["field", "element", "qualifier", "scope_note"]
    readonly_fields = ["field", "element", "qualifier", "scope_note", "source"]
    ordering        = ["field"]
    can_delete      = False
    max_num         = 0
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False

@admin.register(MetadataSchema)
class MetadataSchemaAdmin(admin.ModelAdmin):
    list_display    = ["name", "namespace", "source", "field_count"]
    search_fields   = ["name", "namespace"]
    ordering        = ["name"]
    readonly_fields = ["name", "namespace", "title", "source"]
    inlines         = [MetadataFieldInline]

    def field_count(self, obj):
        return obj.fields.count()
    field_count.short_description = "Fields"

    def has_add_permission(self, request):
        return False  # imported only via management command

@admin.register(MetadataField)
class MetadataFieldAdmin(admin.ModelAdmin):
    list_display    = ["field", "schema", "element", "qualifier", "source"]
    search_fields   = ["field", "element", "qualifier", "scope_note"]
    list_filter     = ["schema"]
    ordering        = ["field"]
    readonly_fields = ["schema", "field", "element", "qualifier", "scope_note", "source"]

    def has_add_permission(self, request):
        return False  # imported only via management command

    def has_delete_permission(self, request, obj=None):
        return False


# ── Submission forms (read-only — imported via management command) ─────────────

class SubmissionFormFieldInline(admin.TabularInline):
    model           = SubmissionFormField
    fk_name         = "form"  # disambiguate from child_form FK
    extra           = 0
    fields          = ["row", "col", "field", "label", "input_type",
                       "is_required", "repeatable", "vocabulary", "child_form_name"]
    readonly_fields = ["row", "col", "field", "label", "input_type",
                       "is_required", "repeatable", "vocabulary", "child_form_name"]
    ordering        = ["row", "col"]
    can_delete      = False
    max_num         = 0

    def has_add_permission(self, request, obj=None):
        return False

@admin.register(SubmissionForm)
class SubmissionFormAdmin(admin.ModelAdmin):
    list_display    = ["name", "contains_required", "field_count", "imported_at"]
    search_fields   = ["name"]
    ordering        = ["name"]
    readonly_fields = ["name", "contains_required", "imported_at"]
    inlines         = [SubmissionFormFieldInline]

    def field_count(self, obj):
        return obj.fields.count()
    field_count.short_description = "Fields"

    def has_add_permission(self, request):
        return False


# ── Submission processes (read-only — imported via management command) ────────

@admin.register(SubmissionStepDefinition)
class SubmissionStepDefinitionAdmin(admin.ModelAdmin):
    list_display    = ["step_id", "type", "mandatory", "scope", "heading", "imported_at"]
    search_fields   = ["step_id", "type", "heading", "processing_class"]
    list_filter     = ["type", "mandatory"]
    ordering        = ["step_id"]
    readonly_fields = ["step_id", "heading", "processing_class", "type",
                       "mandatory", "scope", "imported_at"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class SubmissionProcessStepInline(admin.TabularInline):
    model           = SubmissionProcessStep
    extra           = 0
    fields          = ["sort_order", "step_id", "definition"]
    readonly_fields = ["sort_order", "step_id", "definition"]
    ordering        = ["sort_order"]
    can_delete      = False
    max_num         = 0
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(SubmissionProcess)
class SubmissionProcessAdmin(admin.ModelAdmin):
    list_display    = ["name", "step_count", "imported_at"]
    search_fields   = ["name"]
    ordering        = ["name"]
    readonly_fields = ["name", "imported_at"]
    inlines         = [SubmissionProcessStepInline]

    def step_count(self, obj):
        return obj.steps.count()
    step_count.short_description = "Steps"

    def has_add_permission(self, request):
        return False


# ── Form layouts ──────────────────────────────────────────────────────────────

class FormFieldOverrideInline(admin.TabularInline):
    model   = FormFieldOverride
    extra   = 0
    fields  = ["field_name", "sort_order", "label_override", "hidden"]
    ordering = ["sort_order"]

class FormSectionInline(admin.StackedInline):
    model   = FormSection
    extra   = 0
    fields  = ["key", "label", "sort_order", "collapsed_by_default",
               "helper_text_above", "helper_text_below"]

class FormConditionalBlockInline(admin.TabularInline):
    model   = FormConditionalBlock
    extra   = 0
    fields  = ["sort_order", "trigger_field", "trigger_value",
               "revealed_section", "revealed_fields"]

@admin.register(FormLayout)
class FormLayoutAdmin(admin.ModelAdmin):
    list_display = ["form_name", "profile", "collection", "label", "updated_at"]
    list_filter  = ["profile"]
    search_fields = ["form_name", "label"]
    inlines      = [FormSectionInline, FormConditionalBlockInline]
