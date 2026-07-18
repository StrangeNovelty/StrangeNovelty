from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("ai_assistance", "0006_aicontextmanuscriptlink_manuscript_and_more")]

    operations = [
        migrations.AddField(
            model_name="aicreativerequest",
            name="routing_category",
            field=models.CharField(default="fallback", max_length=16),
        ),
        migrations.AddField(
            model_name="airequest",
            name="routing_category",
            field=models.CharField(default="writing", max_length=16),
        ),
        migrations.AlterField(
            model_name="airequest",
            name="requested_model",
            field=models.CharField(default="deterministic-v1", max_length=160),
        ),
    ]
