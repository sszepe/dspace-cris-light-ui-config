from django.contrib import admin
from .models import (
    CrisLayoutTab, CrisLayoutTab2Box, CrisLayoutBox,
    CrisLayoutBox2Metadata, CrisLayoutBox2Metrics,
    CrisLayoutBox2Vocabulary, CrisLayoutMetadataGroup,
    CrisLayoutTabPolicy, CrisLayoutBoxPolicy,
)


class Tab2BoxInline(admin.TabularInline):
    model = CrisLayoutTab2Box
    extra = 0
    fields = ["tab", "row", "row_style", "cell_style", "boxes"]
    ordering = ["tab", "row"]


class TabPolicyInline(admin.TabularInline):
    model = CrisLayoutTabPolicy
    extra = 0
    fields = ["shortname", "metadata", "group"]


@admin.register(CrisLayoutTab)
class CrisLayoutTabAdmin(admin.ModelAdmin):
    list_display  = ["entity", "shortname", "label", "priority", "leading", "security"]
    list_filter   = ["entity", "security"]
    search_fields = ["entity", "shortname", "label"]
    ordering      = ["entity", "priority"]
    list_editable = ["priority", "leading", "security"]


@admin.register(CrisLayoutTab2Box)
class CrisLayoutTab2BoxAdmin(admin.ModelAdmin):
    list_display  = ["entity", "tab", "row", "boxes"]
    list_filter   = ["entity"]
    search_fields = ["entity", "tab", "boxes"]
    ordering      = ["entity", "tab", "row"]


class BoxPolicyInline(admin.TabularInline):
    model  = CrisLayoutBoxPolicy
    extra  = 0
    fields = ["shortname", "metadata", "group"]


@admin.register(CrisLayoutBox)
class CrisLayoutBoxAdmin(admin.ModelAdmin):
    list_display  = ["entity", "shortname", "label", "box_type", "collapsed", "container", "minor", "security"]
    list_filter   = ["entity", "box_type", "security"]
    search_fields = ["entity", "shortname", "label"]
    ordering      = ["entity", "shortname"]
    list_editable = ["box_type", "security", "collapsed"]
    # Note: Box2Metadata and Box2Metrics link via entity+box charfields (no FK),
    # so they cannot be used as TabularInlines here. Manage via their own admin pages.


@admin.register(CrisLayoutBox2Metadata)
class CrisLayoutBox2MetadataAdmin(admin.ModelAdmin):
    list_display  = ["entity", "box", "row", "cell", "field_type", "metadata", "label", "rendering"]
    list_filter   = ["entity", "field_type"]
    search_fields = ["entity", "box", "metadata", "label"]
    ordering      = ["entity", "box", "row", "cell"]


@admin.register(CrisLayoutBox2Metrics)
class CrisLayoutBox2MetricsAdmin(admin.ModelAdmin):
    list_display  = ["entity", "box", "metric_type_short"]
    list_filter   = ["entity"]
    search_fields = ["entity", "box", "metric_type"]

    def metric_type_short(self, obj):
        return obj.metric_type[:80]
    metric_type_short.short_description = "Metric Types"


@admin.register(CrisLayoutBox2Vocabulary)
class CrisLayoutBox2VocabularyAdmin(admin.ModelAdmin):
    list_display  = ["entity", "box", "vocabulary", "metadata"]
    search_fields = ["entity", "box", "vocabulary"]


@admin.register(CrisLayoutMetadataGroup)
class CrisLayoutMetadataGroupAdmin(admin.ModelAdmin):
    list_display  = ["entity", "parent", "metadata", "label", "rendering"]
    list_filter   = ["entity"]
    search_fields = ["entity", "parent", "metadata", "label"]
    ordering      = ["entity", "parent"]


@admin.register(CrisLayoutTabPolicy)
class CrisLayoutTabPolicyAdmin(admin.ModelAdmin):
    list_display  = ["entity", "shortname", "metadata", "group"]
    list_filter   = ["entity"]
    search_fields = ["entity", "shortname", "metadata"]


@admin.register(CrisLayoutBoxPolicy)
class CrisLayoutBoxPolicyAdmin(admin.ModelAdmin):
    list_display  = ["entity", "shortname", "metadata", "group"]
    list_filter   = ["entity"]
    search_fields = ["entity", "shortname", "metadata"]
