from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """
    Squashed migration: replaces 0001_initial + 0002 + 0003 + 0004.
    On a fresh database this creates all tables in one pass.
    On an existing database with tables already present, entrypoint.sh
    fake-applies this migration so no DDL is re-executed.
    """
    initial = True
    dependencies = []

    operations = [
        # ── EntityCluster ─────────────────────────────────────────────────────
        migrations.CreateModel(
            name="EntityCluster",
            fields=[
                ("id",          models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("key",         models.CharField(max_length=100, unique=True)),
                ("label",       models.CharField(max_length=200)),
                ("description", models.TextField(blank=True, default="")),
                ("sort_order",  models.PositiveIntegerField(default=0)),
                ("enabled",     models.BooleanField(default=True)),
            ],
            options={"ordering": ["sort_order", "label"]},
        ),
        migrations.CreateModel(
            name="EntityTypeEntry",
            fields=[
                ("id",                models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("entity_type_label", models.CharField(max_length=200)),
                ("sort_order",        models.PositiveIntegerField(default=0)),
                ("cluster",           models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                         related_name="entity_types", to="api.entitycluster")),
            ],
            options={"ordering": ["sort_order"]},
        ),
        # ── QuickPreset ───────────────────────────────────────────────────────
        migrations.CreateModel(
            name="QuickPreset",
            fields=[
                ("id",           models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("key",          models.CharField(max_length=100, unique=True)),
                ("label",        models.CharField(max_length=200)),
                ("description",  models.TextField(blank=True, default="")),
                ("base_filters", models.JSONField(default=dict)),
                ("sort_order",   models.PositiveIntegerField(default=0)),
                ("enabled",      models.BooleanField(default=True)),
                ("created_at",   models.DateTimeField(auto_now_add=True)),
                ("updated_at",   models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["sort_order", "label"]},
        ),
        migrations.CreateModel(
            name="QuickPresetFilter",
            fields=[
                ("id",          models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("key",         models.CharField(max_length=100)),
                ("label",       models.CharField(max_length=200)),
                ("facet_name",  models.CharField(max_length=200)),
                ("kind",        models.CharField(choices=[("text","Text"),("date","Date")], max_length=10, default="text")),
                ("placeholder", models.CharField(max_length=200, blank=True, default="")),
                ("sort_order",  models.PositiveIntegerField(default=0)),
                ("preset",      models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                   related_name="filters", to="api.quickpreset")),
            ],
            options={"ordering": ["sort_order"]},
        ),
        # ── SiteSettings ──────────────────────────────────────────────────────
        migrations.CreateModel(
            name="SiteSettings",
            fields=[
                ("id",                               models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("quicklinks_enabled",               models.BooleanField(default=True)),
                ("communities_creation_enabled",     models.BooleanField(default=True)),
                ("communities_role_management_enabled", models.BooleanField(default=True)),
                ("collections_creation_enabled",     models.BooleanField(default=True)),
                ("updated_at",                       models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "Site Settings", "verbose_name_plural": "Site Settings"},
        ),
        # ── MetadataSchema + MetadataField ────────────────────────────────────
        migrations.CreateModel(
            name="MetadataSchema",
            fields=[
                ("id",        models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("name",      models.CharField(max_length=100, unique=True)),
                ("namespace", models.CharField(max_length=500, blank=True, default="")),
                ("title",     models.CharField(max_length=200, blank=True, default="")),
                ("source",    models.CharField(max_length=200, blank=True, default="")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="MetadataField",
            fields=[
                ("id",         models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("element",    models.CharField(max_length=200)),
                ("qualifier",  models.CharField(max_length=200, blank=True, default="")),
                ("field",      models.CharField(max_length=400, unique=True)),
                ("scope_note", models.TextField(blank=True, default="")),
                ("source",     models.CharField(max_length=200, blank=True, default="")),
                ("schema",     models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                  related_name="fields", to="api.metadataschema")),
            ],
            options={"ordering": ["field"],
                     "unique_together": {("schema", "element", "qualifier")}},
        ),
        # ── SubmissionForm + SubmissionFormField ──────────────────────────────
        migrations.CreateModel(
            name="SubmissionForm",
            fields=[
                ("id",               models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("name",             models.CharField(max_length=200, unique=True)),
                ("contains_required", models.BooleanField(default=False)),
                ("imported_at",      models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="SubmissionFormField",
            fields=[
                ("id",               models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("row",              models.PositiveIntegerField(default=0)),
                ("col",              models.PositiveIntegerField(default=0)),
                ("field",            models.CharField(max_length=400, blank=True, default="")),
                ("label",            models.CharField(max_length=500, blank=True, default="")),
                ("input_type",       models.CharField(max_length=20, default="onebox")),
                ("is_required",      models.BooleanField(default=False)),
                ("required_msg",     models.CharField(max_length=500, blank=True, default="")),
                ("repeatable",       models.BooleanField(default=False)),
                ("vocabulary",       models.CharField(max_length=200, blank=True, default="")),
                ("vocabulary_closed", models.BooleanField(default=False)),
                ("value_pairs_name", models.CharField(max_length=200, blank=True, default="")),
                ("hint",             models.TextField(blank=True, default="")),
                ("style",            models.CharField(max_length=200, blank=True, default="")),
                ("regex",            models.CharField(max_length=500, blank=True, default="")),
                ("language_codes",   models.JSONField(default=list)),
                ("type_binds",       models.JSONField(default=list)),
                ("child_form_name",  models.CharField(max_length=200, blank=True, default="")),
                ("form",             models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                        related_name="fields", to="api.submissionform")),
                ("child_form",       models.ForeignKey(null=True, blank=True,
                                                        on_delete=django.db.models.deletion.SET_NULL,
                                                        related_name="parent_fields", to="api.submissionform")),
            ],
            options={"ordering": ["row", "col"]},
        ),
        # ── FormLayout + sections + overrides + conditionals ──────────────────
        migrations.CreateModel(
            name="FormLayout",
            fields=[
                ("id",         models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("form_name",  models.CharField(max_length=200)),
                ("profile",    models.CharField(max_length=100, blank=True, default="plain")),
                ("collection", models.UUIDField(null=True, blank=True)),
                ("label",      models.CharField(max_length=200, blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["form_name", "profile"],
                     "unique_together": {("form_name", "profile", "collection")}},
        ),
        migrations.CreateModel(
            name="FormSection",
            fields=[
                ("id",                   models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("key",                  models.CharField(max_length=100)),
                ("label",                models.CharField(max_length=200)),
                ("sort_order",           models.PositiveIntegerField(default=0)),
                ("collapsed_by_default", models.BooleanField(default=False)),
                ("helper_text_above",    models.TextField(blank=True, default="")),
                ("helper_text_below",    models.TextField(blank=True, default="")),
                ("layout",               models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                            related_name="sections", to="api.formlayout")),
            ],
            options={"ordering": ["sort_order"]},
        ),
        migrations.CreateModel(
            name="FormFieldOverride",
            fields=[
                ("id",             models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("field_name",     models.CharField(max_length=400)),
                ("sort_order",     models.PositiveIntegerField(default=0)),
                ("label_override", models.CharField(max_length=500, blank=True, default="")),
                ("hint_override",  models.TextField(blank=True, default="")),
                ("hidden",         models.BooleanField(default=False)),
                ("section",        models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                      related_name="field_overrides", to="api.formsection")),
            ],
            options={"ordering": ["sort_order"]},
        ),
        migrations.CreateModel(
            name="FormConditionalBlock",
            fields=[
                ("id",               models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("sort_order",       models.PositiveIntegerField(default=0)),
                ("trigger_field",    models.CharField(max_length=400)),
                ("trigger_value",    models.CharField(max_length=200)),
                ("revealed_fields",  models.JSONField(default=list)),
                ("revealed_section", models.CharField(max_length=100, blank=True, default="")),
                ("layout",           models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                        related_name="conditional_blocks", to="api.formlayout")),
            ],
            options={"ordering": ["sort_order"]},
        ),
    ]
