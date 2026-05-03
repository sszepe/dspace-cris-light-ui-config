from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0003_collectionmapping"),
    ]

    operations = [
        migrations.CreateModel(
            name="SubmissionValuePairSet",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=200, unique=True,
                                          help_text='Value pairs name (e.g. "common_iso_languages")')),
                ("dc_term", models.CharField(max_length=200, blank=True,
                                             help_text="dc-term attribute from submission-forms.xml")),
                ("note", models.TextField(blank=True)),
                ("imported_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["name"],
                     "verbose_name": "Submission value-pair set",
                     "verbose_name_plural": "Submission value-pair sets"},
        ),
        migrations.CreateModel(
            name="SubmissionValuePair",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("pair_set", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="pairs",
                    to="api.submissionvaluepairset",
                )),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("displayed_value", models.CharField(max_length=500)),
                ("stored_value", models.CharField(max_length=500, blank=True)),
            ],
            options={"ordering": ["sort_order", "id"],
                     "verbose_name": "Submission value pair",
                     "verbose_name_plural": "Submission value pairs"},
        ),
    ]