from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="CrisLayoutTab",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("entity", models.CharField(max_length=100)),
                ("shortname", models.CharField(max_length=200)),
                ("label", models.CharField(blank=True, default="", max_length=200)),
                ("priority", models.IntegerField(default=0)),
                ("leading", models.BooleanField(default=False, help_text="y/n — is this the leading (default) tab?")),
                ("security", models.CharField(choices=[("PUBLIC","Public"),("ADMINISTRATOR","Administrator"),("OWNER ONLY","Owner Only"),("OWNER & ADMINISTRATOR","Owner & Administrator"),("CUSTOM DATA","Custom Data"),("CUSTOM DATA & ADMINISTRATOR","Custom Data & Administrator")], default="PUBLIC", max_length=60)),
            ],
            options={"ordering": ["entity", "priority"], "verbose_name": "Layout Tab", "verbose_name_plural": "Layout Tabs"},
        ),
        migrations.CreateModel(
            name="CrisLayoutTab2Box",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("entity", models.CharField(max_length=100)),
                ("tab", models.CharField(max_length=200)),
                ("row", models.FloatField(default=1)),
                ("row_style", models.CharField(blank=True, default="", max_length=200)),
                ("cell_style", models.CharField(blank=True, default="", max_length=200)),
                ("boxes", models.CharField(help_text="Comma-separated box shortnames", max_length=500)),
            ],
            options={"ordering": ["entity", "tab", "row"], "verbose_name": "Tab → Box Mapping", "verbose_name_plural": "Tab → Box Mappings"},
        ),
        migrations.CreateModel(
            name="CrisLayoutBox",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("entity", models.CharField(max_length=100)),
                ("shortname", models.CharField(max_length=200)),
                ("label", models.CharField(blank=True, default="", max_length=200)),
                ("box_type", models.CharField(choices=[("METADATA","Metadata"),("RELATION","Relation"),("METRICS","Metrics"),("IIIFVIEWER","IIIF Viewer"),("NETWORKLAB","Network Lab"),("BITSTREAM","Bitstream")], db_column="type", default="METADATA", max_length=20)),
                ("collapsed", models.BooleanField(default=False)),
                ("container", models.BooleanField(default=True)),
                ("minor", models.BooleanField(default=False)),
                ("security", models.CharField(choices=[("PUBLIC","Public"),("ADMINISTRATOR","Administrator"),("OWNER ONLY","Owner Only"),("OWNER & ADMINISTRATOR","Owner & Administrator"),("CUSTOM DATA","Custom Data"),("CUSTOM DATA & ADMINISTRATOR","Custom Data & Administrator")], default="PUBLIC", max_length=60)),
                ("style", models.CharField(blank=True, default="", max_length=200)),
            ],
            options={"ordering": ["entity", "shortname"], "verbose_name": "Layout Box", "verbose_name_plural": "Layout Boxes"},
        ),
        migrations.CreateModel(
            name="CrisLayoutBox2Metadata",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("entity", models.CharField(max_length=100)),
                ("box", models.CharField(max_length=200)),
                ("row", models.FloatField(default=1)),
                ("cell", models.FloatField(default=1)),
                ("field_type", models.CharField(choices=[("METADATA","Metadata"),("BITSTREAM","Bitstream"),("METADATAGROUP","Metadata Group")], db_column="fieldtype", default="METADATA", max_length=20)),
                ("metadata", models.CharField(blank=True, default="", max_length=400)),
                ("value", models.CharField(blank=True, default="", help_text="Fixed value / dc.type filter for BITSTREAMs", max_length=400)),
                ("bundle", models.CharField(blank=True, default="", max_length=200)),
                ("label", models.CharField(blank=True, default="", max_length=500)),
                ("label_as_heading", models.BooleanField(default=False)),
                ("rendering", models.CharField(blank=True, default="", max_length=200)),
                ("values_inline", models.BooleanField(default=False)),
                ("row_style", models.CharField(blank=True, default="", max_length=200)),
                ("cell_style", models.CharField(blank=True, default="", max_length=200)),
                ("style_label", models.CharField(blank=True, default="", max_length=200)),
                ("style_value", models.CharField(blank=True, default="", max_length=200)),
            ],
            options={"ordering": ["entity", "box", "row", "cell"], "verbose_name": "Box → Metadata Field", "verbose_name_plural": "Box → Metadata Fields"},
        ),
        migrations.CreateModel(
            name="CrisLayoutBox2Metrics",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("entity", models.CharField(max_length=100)),
                ("box", models.CharField(max_length=200)),
                ("metric_type", models.TextField(help_text="Comma-separated metric type identifiers")),
            ],
            options={"ordering": ["entity", "box"], "verbose_name": "Box → Metrics", "verbose_name_plural": "Box → Metrics"},
        ),
        migrations.CreateModel(
            name="CrisLayoutBox2Vocabulary",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("entity", models.CharField(max_length=100)),
                ("box", models.CharField(max_length=200)),
                ("vocabulary", models.CharField(max_length=200)),
                ("metadata", models.CharField(blank=True, default="", max_length=400)),
            ],
            options={"ordering": ["entity", "box"], "verbose_name": "Box → Hierarchical Vocabulary", "verbose_name_plural": "Box → Hierarchical Vocabularies"},
        ),
        migrations.CreateModel(
            name="CrisLayoutMetadataGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("entity", models.CharField(max_length=100)),
                ("parent", models.CharField(help_text="Parent metadata field (the group key)", max_length=400)),
                ("field_type", models.CharField(choices=[("METADATA","Metadata"),("BITSTREAM","Bitstream"),("METADATAGROUP","Metadata Group")], db_column="fieldtype", default="METADATA", max_length=20)),
                ("metadata", models.CharField(max_length=400)),
                ("value", models.CharField(blank=True, default="", max_length=400)),
                ("bundle", models.CharField(blank=True, default="", max_length=200)),
                ("label", models.CharField(blank=True, default="", max_length=500)),
                ("rendering", models.CharField(blank=True, default="", max_length=200)),
                ("style_label", models.CharField(blank=True, default="", max_length=200)),
                ("style_value", models.CharField(blank=True, default="", max_length=200)),
            ],
            options={"ordering": ["entity", "parent", "id"], "verbose_name": "Metadata Group Field", "verbose_name_plural": "Metadata Group Fields"},
        ),
        migrations.CreateModel(
            name="CrisLayoutTabPolicy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("entity", models.CharField(max_length=100)),
                ("shortname", models.CharField(max_length=200)),
                ("metadata", models.CharField(max_length=400)),
                ("group", models.CharField(blank=True, default="", max_length=200)),
            ],
            options={"ordering": ["entity", "shortname"], "verbose_name": "Tab Policy", "verbose_name_plural": "Tab Policies"},
        ),
        migrations.CreateModel(
            name="CrisLayoutBoxPolicy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("entity", models.CharField(max_length=100)),
                ("shortname", models.CharField(max_length=200)),
                ("metadata", models.CharField(max_length=400)),
                ("group", models.CharField(blank=True, default="", max_length=200)),
            ],
            options={"ordering": ["entity", "shortname"], "verbose_name": "Box Policy", "verbose_name_plural": "Box Policies"},
        ),
        migrations.AlterUniqueTogether(name="crislayouttab", unique_together={("entity", "shortname")}),
        migrations.AlterUniqueTogether(name="crislayoutbox", unique_together={("entity", "shortname")}),
        migrations.AlterUniqueTogether(name="crislayoutbox2metrics", unique_together={("entity", "box")}),
    ]
