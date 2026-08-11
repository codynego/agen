from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="approval_mode",
            field=models.CharField(
                choices=[("always_ask", "Always ask"), ("balanced", "Balanced"), ("auto_connect", "Auto-connect")],
                default="balanced",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="goal_categories",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="integration_interests",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="onboarding_completed",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="onboarding_completed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
