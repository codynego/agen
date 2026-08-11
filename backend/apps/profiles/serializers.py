from rest_framework import serializers

from apps.agents.models import Agent

from .models import UserProfile


GOAL_CHOICES = [
    "work",
    "research",
    "travel",
    "shopping",
    "personal_admin",
    "business",
]

INTEGRATION_CHOICES = ["email_calendar", "files", "payments", "business_tools"]


class OnboardingSerializer(serializers.Serializer):
    agent_name = serializers.CharField(max_length=120)
    goals = serializers.ListField(
        child=serializers.ChoiceField(choices=GOAL_CHOICES),
        min_length=1,
        max_length=6,
    )
    approval_mode = serializers.ChoiceField(choices=UserProfile.ApprovalMode.choices)
    integrations = serializers.ListField(
        child=serializers.ChoiceField(choices=INTEGRATION_CHOICES),
        required=False,
        allow_empty=True,
        max_length=4,
    )

    def validate(self, attrs):
        if "trust_score" in self.initial_data:
            raise serializers.ValidationError({"trust_score": "Trust scores are calculated by the network and cannot be set by users."})
        attrs["agent_name"] = attrs["agent_name"].strip()
        if not attrs["agent_name"]:
            raise serializers.ValidationError({"agent_name": "Give your agent a name."})
        attrs["goals"] = list(dict.fromkeys(attrs["goals"]))
        attrs["integrations"] = list(dict.fromkeys(attrs.get("integrations", [])))
        return attrs


class OnboardingStatusSerializer(serializers.Serializer):
    onboarding_completed = serializers.BooleanField()
    agent_id = serializers.UUIDField(source="agent.agent_id")
    network_handle = serializers.CharField(source="agent.network_handle")
    agent_name = serializers.CharField(source="agent.name")
    approval_mode = serializers.CharField(source="profile.approval_mode")
    goals = serializers.ListField(source="profile.goal_categories")
    integrations = serializers.ListField(source="profile.integration_interests")
    trust_score = serializers.DecimalField(source="agent.trust_score", max_digits=4, decimal_places=1, read_only=True)
    trust_level = serializers.CharField(source="agent.trust_level", read_only=True)


def onboarding_status(user, profile: UserProfile, agent: Agent) -> dict:
    return {
        "onboarding_completed": profile.onboarding_completed,
        "profile": profile,
        "agent": agent,
    }
