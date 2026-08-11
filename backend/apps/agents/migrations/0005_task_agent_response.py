from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("agents", "0004_agentconnection_datagrant_task_agentconnection_task_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="agent_response",
            field=models.TextField(blank=True),
        ),
    ]
