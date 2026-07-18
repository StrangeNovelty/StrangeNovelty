import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("story_engine_next", "0001_initial"),
        ("workspaces", "0001_initial"),
    ]
    operations = [
        migrations.CreateModel(
            name="WorldBibleEntry",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("title", models.CharField(max_length=240)),
                ("content", models.TextField(blank=True)),
                ("order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "workspace",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="world_bible_entries",
                        to="workspaces.workspace",
                    ),
                ),
            ],
            options={"ordering": ("order", "title", "id")},
        ),
        migrations.AddConstraint(
            model_name="worldbibleentry",
            constraint=models.UniqueConstraint(
                fields=("workspace", "title"), name="next_world_bible_title_uniq"
            ),
        ),
    ]
