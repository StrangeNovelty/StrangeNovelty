import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("ai_assistance", "0008_brainstormsession"),
        ("decks", "0003_saveddraw_selected_categories_and_more"),
    ]
    operations = [
        migrations.CreateModel(
            name="BrainstormCardSelection",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("manual_text", models.TextField(blank=True)),
                ("order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "card",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="brainstorm_selections",
                        to="decks.deckcard",
                    ),
                ),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="card_selections",
                        to="ai_assistance.brainstormsession",
                    ),
                ),
            ],
            options={"ordering": ("order", "created_at")},
        ),
        migrations.AddConstraint(
            model_name="brainstormcardselection",
            constraint=models.UniqueConstraint(
                fields=("session", "order"), name="next_brainstorm_card_order_uniq"
            ),
        ),
    ]
