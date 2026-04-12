from rest_framework import serializers
from .models import (
    CrisLayoutTab, CrisLayoutTab2Box, CrisLayoutBox,
    CrisLayoutBox2Metadata, CrisLayoutBox2Metrics,
    CrisLayoutBox2Vocabulary, CrisLayoutMetadataGroup,
    CrisLayoutTabPolicy, CrisLayoutBoxPolicy,
)


class CrisLayoutTabSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrisLayoutTab
        fields = ["id", "entity", "shortname", "label", "priority", "leading", "security"]


class CrisLayoutTab2BoxSerializer(serializers.ModelSerializer):
    box_list = serializers.ReadOnlyField()
    class Meta:
        model = CrisLayoutTab2Box
        fields = ["id", "entity", "tab", "row", "row_style", "cell_style", "boxes", "box_list"]


class CrisLayoutBox2MetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrisLayoutBox2Metadata
        fields = [
            "id", "entity", "box", "row", "cell", "field_type",
            "metadata", "value", "bundle", "label", "label_as_heading",
            "rendering", "values_inline", "row_style", "cell_style",
            "style_label", "style_value",
        ]


class CrisLayoutBox2MetricsSerializer(serializers.ModelSerializer):
    metric_list = serializers.ReadOnlyField()
    class Meta:
        model = CrisLayoutBox2Metrics
        fields = ["id", "entity", "box", "metric_type", "metric_list"]


class CrisLayoutBox2VocabularySerializer(serializers.ModelSerializer):
    class Meta:
        model = CrisLayoutBox2Vocabulary
        fields = ["id", "entity", "box", "vocabulary", "metadata"]


class CrisLayoutMetadataGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrisLayoutMetadataGroup
        fields = [
            "id", "entity", "parent", "field_type", "metadata",
            "value", "bundle", "label", "rendering", "style_label", "style_value",
        ]


class CrisLayoutTabPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = CrisLayoutTabPolicy
        fields = ["id", "entity", "shortname", "metadata", "group"]


class CrisLayoutBoxPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = CrisLayoutBoxPolicy
        fields = ["id", "entity", "shortname", "metadata", "group"]


class CrisLayoutBoxSerializer(serializers.ModelSerializer):
    # fields_data, metrics, and policies are populated explicitly in
    # CrisLayoutEntityView using char-field lookups (entity + box shortname).
    # They are not FK-based relations, so we declare them as empty write-only
    # defaults here; the entity view always overwrites them before returning.
    fields_data = serializers.SerializerMethodField()
    metrics     = serializers.SerializerMethodField()
    policies    = serializers.SerializerMethodField()

    class Meta:
        model = CrisLayoutBox
        fields = [
            "id", "entity", "shortname", "label", "box_type",
            "collapsed", "container", "minor", "security", "style",
            "fields_data", "metrics", "policies",
        ]

    def get_fields_data(self, obj):
        # Populated by the entity view; return empty list as safe default.
        return []

    def get_metrics(self, obj):
        # Populated by the entity view; return None as safe default.
        return None

    def get_policies(self, obj):
        # Populated by the entity view; return empty list as safe default.
        return []


class CrisLayoutBoxWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrisLayoutBox
        fields = ["entity", "shortname", "label", "box_type", "collapsed", "container", "minor", "security", "style"]


# ── Full entity layout (used by cockpit entity view) ──────────────────────────

class EntityLayoutSerializer(serializers.Serializer):
    """Aggregated layout for one entity — all tabs, boxes and fields."""
    entity   = serializers.CharField()
    tabs     = CrisLayoutTabSerializer(many=True)
    tab2box  = CrisLayoutTab2BoxSerializer(many=True)
    boxes    = CrisLayoutBoxSerializer(many=True)
    metadata_groups = CrisLayoutMetadataGroupSerializer(many=True)
    tab_policies    = CrisLayoutTabPolicySerializer(many=True)
