import uuid

from django.db import migrations, models


def assign_network_handles(apps, schema_editor):
    Agent = apps.get_model("agents", "Agent")
    for agent in Agent.objects.all().iterator():
        prefix = "agen" if agent.kind == "personal" else "agent"
        suffix = agent.agent_id.hex[:12]
        candidate = f"{prefix}-{suffix}"
        while Agent.objects.filter(network_handle=candidate).exclude(pk=agent.pk).exists():
            candidate = f"{prefix}-{uuid.uuid4().hex[:12]}"
        Agent.objects.filter(pk=agent.pk).update(network_handle=candidate)


class Migration(migrations.Migration):
    dependencies = [
        ("agents", "0002_agent_hosting_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="agent",
            name="network_handle",
            field=models.SlugField(blank=True, max_length=140, null=True),
        ),
        migrations.RunPython(assign_network_handles, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="agent",
            name="network_handle",
            field=models.SlugField(db_index=True, editable=False, max_length=140, unique=True),
        ),
    ]
