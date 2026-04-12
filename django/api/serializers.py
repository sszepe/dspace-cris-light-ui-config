from rest_framework import serializers
from .models import (
    EntityCluster, EntityTypeEntry,
    QuickPreset, QuickPresetFilter, SiteSettings,
    CollectionMapping,
    MetadataSchema, MetadataField,
    SubmissionForm, SubmissionFormField,
    SubmissionStepDefinition, SubmissionProcess, SubmissionProcessStep,
    FormLayout, FormSection, FormFieldOverride, FormConditionalBlock,
)


# ── Cluster ───────────────────────────────────────────────────────────────────

class EntityTypeEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model  = EntityTypeEntry
        fields = ["id", "entity_type_label", "sort_order"]

class EntityClusterSerializer(serializers.ModelSerializer):
    entity_types = EntityTypeEntrySerializer(many=True, read_only=True)
    class Meta:
        model  = EntityCluster
        fields = ["id", "key", "label", "description", "sort_order", "enabled", "entity_types"]

class EntityClusterWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model  = EntityCluster
        fields = ["key", "label", "description", "sort_order", "enabled"]


# ── QuickPreset ───────────────────────────────────────────────────────────────

class QuickPresetFilterSerializer(serializers.ModelSerializer):
    class Meta:
        model  = QuickPresetFilter
        fields = ["id", "key", "label", "facet_name", "kind", "placeholder", "sort_order"]

class QuickPresetSerializer(serializers.ModelSerializer):
    filters = QuickPresetFilterSerializer(many=True, read_only=True)
    class Meta:
        model  = QuickPreset
        fields = ["id", "key", "label", "description", "base_filters",
                  "sort_order", "enabled", "filters", "created_at", "updated_at"]

class QuickPresetWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model  = QuickPreset
        fields = ["key", "label", "description", "base_filters", "sort_order", "enabled"]


# ── Site settings ─────────────────────────────────────────────────────────────

class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SiteSettings
        fields = ["quicklinks_enabled", "communities_creation_enabled",
                  "communities_role_management_enabled", "collections_creation_enabled",
                  "updated_at"]


# ── Collection mapping ────────────────────────────────────────────────────────

class CollectionMappingSerializer(serializers.ModelSerializer):
    """Read serializer — surfaces conditions as { dcTypeIncludes, risfundingStatusIn }."""
    conditions = serializers.SerializerMethodField()

    class Meta:
        model  = CollectionMapping
        fields = ["id", "entity_type", "collection_id", "label",
                  "conditions", "sort_order", "created_at", "updated_at"]

    def get_conditions(self, obj):
        dc   = obj.dc_type_includes or []
        stat = obj.risfunding_status_in or []
        if not dc and not stat:
            return None
        out = {}
        if dc:   out["dcTypeIncludes"]     = dc
        if stat: out["risfundingStatusIn"] = stat
        return out


class CollectionMappingWriteSerializer(serializers.ModelSerializer):
    """Write serializer — accepts camelCase aliases and nested conditions."""
    entityType         = serializers.CharField(source="entity_type",         required=False)
    collectionId       = serializers.CharField(source="collection_id",       required=False)
    dcTypeIncludes     = serializers.ListField(child=serializers.CharField(),
                             source="dc_type_includes",     required=False, default=list)
    risfundingStatusIn = serializers.ListField(child=serializers.CharField(),
                             source="risfunding_status_in", required=False, default=list)

    class Meta:
        model  = CollectionMapping
        fields = ["entity_type", "collection_id", "label",
                  "dc_type_includes", "risfunding_status_in", "sort_order",
                  "entityType", "collectionId", "dcTypeIncludes", "risfundingStatusIn"]

    def to_internal_value(self, data):
        data = data.copy() if hasattr(data, "copy") else dict(data)
        conditions = data.pop("conditions", None)
        if isinstance(conditions, dict):
            for k, snake in [("dcTypeIncludes", "dcTypeIncludes"),
                              ("risfundingStatusIn", "risfundingStatusIn"),
                              ("dc_type_includes", "dc_type_includes"),
                              ("risfunding_status_in", "risfunding_status_in")]:
                if k in conditions:
                    data.setdefault(k, conditions[k])
        return super().to_internal_value(data)


# ── Metadata registry ─────────────────────────────────────────────────────────

class MetadataFieldSerializer(serializers.ModelSerializer):
    schema_name = serializers.CharField(source="schema.name", read_only=True)
    class Meta:
        model  = MetadataField
        fields = ["id", "schema_name", "element", "qualifier", "field", "scope_note", "source"]

class MetadataSchemaSerializer(serializers.ModelSerializer):
    field_count = serializers.IntegerField(source="fields.count", read_only=True)
    class Meta:
        model  = MetadataSchema
        fields = ["id", "name", "namespace", "title", "source", "field_count"]

class MetadataSchemaDetailSerializer(serializers.ModelSerializer):
    fields = MetadataFieldSerializer(many=True, read_only=True)
    class Meta:
        model  = MetadataSchema
        fields = ["id", "name", "namespace", "title", "source", "fields"]


# ── Submission forms ──────────────────────────────────────────────────────────

class SubmissionFormFieldSerializer(serializers.ModelSerializer):
    child_form_name_resolved = serializers.SerializerMethodField()

    class Meta:
        model  = SubmissionFormField
        fields = [
            "id", "row", "col",
            "field", "label", "input_type",
            "is_required", "required_msg",
            "repeatable", "vocabulary", "vocabulary_closed",
            "value_pairs_name", "hint", "style", "regex",
            "language_codes", "type_binds",
            "child_form_name", "child_form", "child_form_name_resolved",
        ]

    def get_child_form_name_resolved(self, obj):
        return obj.child_form.name if obj.child_form_id else obj.child_form_name or None

class SubmissionFormSerializer(serializers.ModelSerializer):
    fields      = SubmissionFormFieldSerializer(many=True, read_only=True)
    field_count = serializers.IntegerField(source="fields.count", read_only=True)
    class Meta:
        model  = SubmissionForm
        fields = ["id", "name", "contains_required", "field_count", "fields", "imported_at"]

class SubmissionFormListSerializer(serializers.ModelSerializer):
    field_count          = serializers.IntegerField(source="fields.count", read_only=True)
    required_field_count = serializers.SerializerMethodField()
    class Meta:
        model  = SubmissionForm
        fields = ["id", "name", "contains_required", "required_field_count",
                  "field_count", "imported_at"]

    def get_required_field_count(self, obj):
        return obj.fields.filter(is_required=True).count()


# ── Submission processes ──────────────────────────────────────────────────────

class SubmissionStepDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SubmissionStepDefinition
        fields = ["id", "step_id", "heading", "processing_class", "type",
                  "mandatory", "scope", "imported_at"]

class SubmissionProcessStepSerializer(serializers.ModelSerializer):
    """One step inside a process, with resolved definition fields."""
    type             = serializers.CharField(source="definition.type",             read_only=True, default=None)
    mandatory        = serializers.BooleanField(source="definition.mandatory",     read_only=True, default=True)
    heading          = serializers.CharField(source="definition.heading",          read_only=True, default="")
    processing_class = serializers.CharField(source="definition.processing_class", read_only=True, default="")

    class Meta:
        model  = SubmissionProcessStep
        fields = ["id", "sort_order", "step_id",
                  "type", "mandatory", "heading", "processing_class"]

class SubmissionProcessSerializer(serializers.ModelSerializer):
    steps      = SubmissionProcessStepSerializer(many=True, read_only=True)
    step_count = serializers.IntegerField(source="steps.count", read_only=True)
    class Meta:
        model  = SubmissionProcess
        fields = ["id", "name", "step_count", "steps", "imported_at"]

class SubmissionProcessListSerializer(serializers.ModelSerializer):
    step_count = serializers.IntegerField(source="steps.count", read_only=True)
    class Meta:
        model  = SubmissionProcess
        fields = ["id", "name", "step_count", "imported_at"]


# ── Form layout ───────────────────────────────────────────────────────────────

class FormFieldOverrideSerializer(serializers.ModelSerializer):
    class Meta:
        model  = FormFieldOverride
        fields = ["id", "field_name", "sort_order", "label_override", "hint_override", "hidden"]

class FormConditionalBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model  = FormConditionalBlock
        fields = ["id", "sort_order", "trigger_field", "trigger_value",
                  "revealed_fields", "revealed_section"]

class FormSectionSerializer(serializers.ModelSerializer):
    field_overrides = FormFieldOverrideSerializer(many=True, read_only=True)
    class Meta:
        model  = FormSection
        fields = ["id", "key", "label", "sort_order", "collapsed_by_default",
                  "helper_text_above", "helper_text_below", "field_overrides"]

class FormLayoutSerializer(serializers.ModelSerializer):
    sections           = FormSectionSerializer(many=True, read_only=True)
    conditional_blocks = FormConditionalBlockSerializer(many=True, read_only=True)
    class Meta:
        model  = FormLayout
        fields = ["id", "form_name", "profile", "collection", "label",
                  "created_at", "updated_at", "sections", "conditional_blocks"]

class FormLayoutWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model  = FormLayout
        fields = ["form_name", "profile", "collection", "label"]
