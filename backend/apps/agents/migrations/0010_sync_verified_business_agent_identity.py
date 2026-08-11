from django.db import migrations


def sync_verified_business_agent_identity(apps, schema_editor):
    Agent = apps.get_model("agents", "Agent")
    ManagedAgentProfile = apps.get_model("agents", "ManagedAgentProfile")

    profiles = ManagedAgentProfile.objects.filter(
        verification_status="verified",
        agent__verified=False,
    ).select_related("agent")
    for profile in profiles.iterator():
        Agent.objects.filter(pk=profile.agent_id).update(
            verified=True,
            identity_verified_at=profile.updated_at,
        )


class Migration(migrations.Migration):
    dependencies = [("agents", "0009_agentcatalogitem_published_and_more")]

    operations = [migrations.RunPython(sync_verified_business_agent_identity, migrations.RunPython.noop)]
