from rest_framework import serializers

from .models import Agent, AgentActivity, TrustEvent


class AgentActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentActivity
        fields = ["id", "title", "detail", "created_at"]


class AgentSerializer(serializers.ModelSerializer):
    activities = AgentActivitySerializer(many=True, read_only=True)

    class Meta:
        model = Agent
        fields = [
            "id",
            "agent_id",
            "name",
            "slug",
            "kind",
            "hosting_type",
            "status",
            "category",
            "company_name",
            "location",
            "endpoint",
            "summary",
            "trust_score",
            "trust_level",
            "verified",
            "identity_key_fingerprint",
            "identity_verified_at",
            "online",
            "capabilities",
            "allowed_actions",
            "blocked_actions",
            "created_at",
            "updated_at",
            "activities",
        ]
        read_only_fields = [
            "agent_id",
            "slug",
            "trust_score",
            "trust_level",
            "verified",
            "identity_key_fingerprint",
            "identity_verified_at",
            "created_at",
            "updated_at",
        ]


class PersonalAgentProvisionSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120, required=False, allow_blank=True)


class BusinessAgentRegistrationSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    company_name = serializers.CharField(max_length=120)
    category = serializers.CharField(max_length=80)
    summary = serializers.CharField(required=False, allow_blank=True)
    hosting_type = serializers.ChoiceField(choices=Agent.HostingType.choices)
    endpoint = serializers.URLField(required=False, allow_blank=True, max_length=255)
    capabilities = serializers.ListField(
        child=serializers.CharField(max_length=80),
        required=False,
        allow_empty=True,
    )

    def validate(self, attrs):
        endpoint = attrs.get("endpoint", "")
        if attrs["hosting_type"] == Agent.HostingType.EXTERNAL and not endpoint:
            raise serializers.ValidationError({"endpoint": "An HTTPS endpoint is required for an external agent."})
        if endpoint and not endpoint.startswith("https://"):
            raise serializers.ValidationError({"endpoint": "Agent endpoints must use HTTPS."})
        return attrs


class PublicAgentVerificationSerializer(serializers.ModelSerializer):
    trust_event_count = serializers.IntegerField(read_only=True)
    verification_url = serializers.SerializerMethodField()

    class Meta:
        model = Agent
        fields = [
            "agent_id",
            "name",
            "kind",
            "hosting_type",
            "status",
            "summary",
            "endpoint",
            "capabilities",
            "allowed_actions",
            "trust_score",
            "trust_level",
            "verified",
            "identity_key_fingerprint",
            "identity_verified_at",
            "trust_event_count",
            "verification_url",
            "created_at",
            "updated_at",
        ]

    def get_verification_url(self, obj):
        request = self.context.get("request")
        path = f"/api/agents/verify/{obj.agent_id}/"
        return request.build_absolute_uri(path) if request else path


class PublicTrustEventSerializer(serializers.ModelSerializer):
    source_agent_id = serializers.UUIDField(source="source_agent.agent_id", read_only=True, allow_null=True)

    class Meta:
        model = TrustEvent
        fields = ["event_id", "source_agent_id", "category", "outcome", "score_delta", "evidence_hash", "created_at"]


class DashboardSerializer(serializers.Serializer):
    greeting = serializers.CharField()
    metrics = serializers.DictField(child=serializers.IntegerField())
    personal_agent = AgentSerializer(required=False, allow_null=True)
    featured_agents = AgentSerializer(many=True, required=False)
    recent_activity = serializers.ListField(child=serializers.DictField())
