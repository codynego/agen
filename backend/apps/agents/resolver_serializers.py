from rest_framework import serializers

from .models import AgentConnection, Task, TaskCandidate, TaskResult, TaskStep
from .resolver import ALLOWED_SCOPES


class DiscoveryRequestSerializer(serializers.Serializer):
    request_text = serializers.CharField(max_length=4000)
    capabilities = serializers.ListField(
        child=serializers.RegexField(r"^[a-z][a-z0-9_]{1,79}$"),
        required=False,
        allow_empty=False,
        max_length=8,
    )
    location = serializers.CharField(max_length=120, required=False, allow_blank=True)
    max_budget = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, min_value=0)
    currency = serializers.RegexField(r"^[A-Z]{3,8}$", required=False, default="NGN")

    def validate(self, attrs):
        forbidden = {"trust_score", "minimum_trust_score"} & set(self.initial_data)
        if forbidden:
            raise serializers.ValidationError({field: "Trust is calculated by the network and cannot be supplied." for field in forbidden})
        attrs["request_text"] = attrs["request_text"].strip()
        if not attrs["request_text"]:
            raise serializers.ValidationError({"request_text": "Describe the task you want completed."})
        return attrs


class TaskStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskStep
        fields = ["position", "title", "status", "updated_at"]


class CandidateSerializer(serializers.ModelSerializer):
    agent_id = serializers.UUIDField(source="agent.agent_id")
    network_handle = serializers.CharField(source="agent.network_handle")
    name = serializers.CharField(source="agent.name")
    category = serializers.CharField(source="agent.category")
    location = serializers.CharField(source="agent.location")
    capabilities = serializers.ListField(source="agent.capabilities")
    trust_score = serializers.DecimalField(source="agent.trust_score", max_digits=4, decimal_places=1)
    trust_level = serializers.CharField(source="agent.trust_level")
    verified = serializers.BooleanField(source="agent.verified")

    class Meta:
        model = TaskCandidate
        fields = [
            "rank",
            "match_score",
            "agent_id",
            "network_handle",
            "name",
            "category",
            "location",
            "capabilities",
            "trust_score",
            "trust_level",
            "verified",
            "reasons",
        ]


class TaskSerializer(serializers.ModelSerializer):
    candidates = CandidateSerializer(many=True, read_only=True)
    steps = TaskStepSerializer(many=True, read_only=True)

    class Meta:
        model = Task
        fields = ["task_id", "request_text", "agent_response", "discovery_spec", "status", "risk_level", "candidates", "steps", "created_at", "updated_at"]


class ConnectionRequestSerializer(serializers.Serializer):
    candidate_handle = serializers.SlugField(max_length=140)
    scopes = serializers.ListField(
        child=serializers.ChoiceField(choices=sorted(ALLOWED_SCOPES)),
        required=False,
        default=list,
        max_length=len(ALLOWED_SCOPES),
    )

    def validate_scopes(self, value):
        return list(dict.fromkeys(value))


class ConnectionApprovalSerializer(serializers.Serializer):
    scopes = serializers.ListField(
        child=serializers.ChoiceField(choices=sorted(ALLOWED_SCOPES)),
        required=False,
        default=list,
        max_length=len(ALLOWED_SCOPES),
    )

    def validate_scopes(self, value):
        return list(dict.fromkeys(value))


class ConnectionSerializer(serializers.ModelSerializer):
    task_id = serializers.UUIDField(source="task.task_id")
    provider = serializers.SerializerMethodField()
    data_grant = serializers.SerializerMethodField()

    class Meta:
        model = AgentConnection
        fields = ["connection_id", "task_id", "status", "auto_approved", "requested_scopes", "trust_score_snapshot", "provider", "data_grant", "approved_at", "created_at"]

    def get_provider(self, obj):
        provider = obj.provider_agent
        data = {
            "agent_id": provider.agent_id,
            "network_handle": provider.network_handle,
            "name": provider.name,
            "capabilities": provider.capabilities,
        }
        if obj.status in {AgentConnection.Status.APPROVED, AgentConnection.Status.ACTIVE}:
            data["endpoint"] = provider.endpoint
        return data

    def get_data_grant(self, obj):
        try:
            grant = obj.data_grant
        except AgentConnection.data_grant.RelatedObjectDoesNotExist:
            return None
        return {"grant_id": grant.grant_id, "scopes": grant.scopes, "expires_at": grant.expires_at, "active": grant.active}


class ProviderConnectionSerializer(serializers.ModelSerializer):
    requester_handle = serializers.CharField(source="requester_agent.network_handle")
    task_spec = serializers.SerializerMethodField()
    grant = serializers.SerializerMethodField()

    class Meta:
        model = AgentConnection
        fields = ["connection_id", "requester_handle", "status", "task_spec", "grant", "approved_at", "created_at"]

    def get_task_spec(self, obj):
        try:
            grant = obj.data_grant
        except AgentConnection.data_grant.RelatedObjectDoesNotExist:
            return {}
        if not grant.active:
            return {}
        source = obj.task.discovery_spec
        scopes = set(grant.scopes)
        task_spec = {}
        if "task_context" in scopes:
            task_spec.update({"brief": source.get("brief", ""), "capabilities": source.get("capabilities", [])})
        if "location" in scopes and source.get("location"):
            task_spec["location"] = source["location"]
        if "budget_limit" in scopes and source.get("budget"):
            task_spec["budget"] = source["budget"]
        return task_spec

    def get_grant(self, obj):
        try:
            grant = obj.data_grant
        except AgentConnection.data_grant.RelatedObjectDoesNotExist:
            return None
        return {"grant_id": grant.grant_id, "scopes": grant.scopes, "expires_at": grant.expires_at, "active": grant.active}


class TaskResultInputSerializer(serializers.Serializer):
    summary = serializers.CharField(max_length=8000)
    structured_result = serializers.JSONField(required=False, default=dict)
    evidence_hash = serializers.RegexField(r"^[a-fA-F0-9]{64}$", required=False, allow_blank=True)


class TaskResultSerializer(serializers.ModelSerializer):
    task_id = serializers.UUIDField(source="task.task_id")

    class Meta:
        model = TaskResult
        fields = ["result_id", "task_id", "summary", "structured_result", "evidence_hash", "created_at", "delivered_at"]
