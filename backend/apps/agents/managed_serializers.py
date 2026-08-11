from django.conf import settings
from rest_framework import serializers

from .conversation_crypto import decrypt_message
from .managed_agents import INDUSTRY_TEMPLATES, readiness
from .models import (
    Agent,
    AgentAuditEvent,
    AgentCatalogItem,
    AgentKnowledgeSource,
    AgentTestRun,
    AgentToolConnection,
    ManagedAgentProfile,
)


class ManagedProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManagedAgentProfile
        fields = [
            "template_key", "verification_status", "verification_level", "requested_verification_level",
            "verification_method", "business_domain", "country", "registration_number", "business_phone",
            "supporting_url", "evidence_notes", "instructions", "tone", "human_handoff",
            "verification_submitted_at", "updated_at",
        ]
        read_only_fields = ["verification_status", "verification_level", "verification_method", "verification_submitted_at", "updated_at"]


class KnowledgeSerializer(serializers.ModelSerializer):
    content = serializers.SerializerMethodField()

    class Meta:
        model = AgentKnowledgeSource
        fields = ["source_id", "kind", "title", "content", "source_url", "active", "created_at", "updated_at"]

    def get_content(self, obj):
        return decrypt_message(obj.content_ciphertext)


class KnowledgeInputSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=AgentKnowledgeSource.Kind.choices, default=AgentKnowledgeSource.Kind.NOTE)
    title = serializers.CharField(max_length=180)
    content = serializers.CharField(max_length=30000)
    source_url = serializers.URLField(required=False, allow_blank=True)


class CatalogItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentCatalogItem
        fields = ["item_id", "name", "sku", "description", "price", "currency", "availability", "active", "metadata", "created_at", "updated_at"]
        read_only_fields = ["item_id", "created_at", "updated_at"]


class ToolConnectionSerializer(serializers.ModelSerializer):
    has_secret_config = serializers.SerializerMethodField()

    class Meta:
        model = AgentToolConnection
        fields = ["connection_id", "provider", "display_name", "status", "scopes", "has_secret_config", "last_tested_at", "created_at", "updated_at"]

    def get_has_secret_config(self, obj):
        return bool(obj.config_ciphertext)


class ToolInputSerializer(serializers.Serializer):
    provider = serializers.RegexField(r"^[a-z][a-z0-9_-]{1,79}$")
    display_name = serializers.CharField(max_length=120)
    scopes = serializers.ListField(child=serializers.CharField(max_length=80), required=False, default=list, max_length=20)
    secret_config = serializers.JSONField(required=False, default=dict, write_only=True)


class TestRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentTestRun
        fields = ["run_id", "prompt", "response", "status", "matched_sources", "created_at"]


class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentAuditEvent
        fields = ["event_id", "action", "detail", "metadata", "created_at"]


class ManagedSetupSerializer(serializers.Serializer):
    agent = serializers.SerializerMethodField()
    profile = ManagedProfileSerializer()
    knowledge = KnowledgeSerializer(many=True)
    catalog = CatalogItemSerializer(many=True)
    tools = ToolConnectionSerializer(many=True)
    tests = TestRunSerializer(many=True)
    audit = AuditEventSerializer(many=True)
    templates = serializers.SerializerMethodField()
    readiness = serializers.SerializerMethodField()
    development_verification_enabled = serializers.SerializerMethodField()

    def get_agent(self, obj):
        agent = obj["agent"]
        return {
            "agent_id": agent.agent_id,
            "network_handle": agent.network_handle,
            "name": agent.name,
            "company_name": agent.company_name,
            "category": agent.category,
            "summary": agent.summary,
            "status": agent.status,
            "verified": agent.verified,
            "trust_score": agent.trust_score,
            "capabilities": agent.capabilities,
            "allowed_actions": agent.allowed_actions,
            "blocked_actions": agent.blocked_actions,
        }

    def get_templates(self, obj):
        return [{"key": key, **value, "starter_knowledge": None} for key, value in INDUSTRY_TEMPLATES.items()]

    def get_readiness(self, obj):
        return readiness(obj["agent"])

    def get_development_verification_enabled(self, obj):
        return bool(settings.DEBUG and settings.BUSINESS_DEV_VERIFICATION_CODE)


class ManagedSettingsInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120, required=False)
    company_name = serializers.CharField(max_length=120, required=False)
    summary = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    instructions = serializers.CharField(required=False, allow_blank=True, max_length=12000)
    tone = serializers.CharField(required=False, allow_blank=True, max_length=80)
    human_handoff = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    capabilities = serializers.ListField(child=serializers.RegexField(r"^[a-z][a-z0-9_]{1,79}$"), required=False, max_length=20)
    allowed_actions = serializers.ListField(child=serializers.CharField(max_length=80), required=False, max_length=30)
    blocked_actions = serializers.ListField(child=serializers.CharField(max_length=80), required=False, max_length=30)


class VerificationInputSerializer(serializers.Serializer):
    method = serializers.ChoiceField(choices=["domain", "manual", "development"])
    domain = serializers.CharField(max_length=160, required=False, allow_blank=True)
    country = serializers.CharField(max_length=80, required=False, allow_blank=True)
    registration_number = serializers.CharField(max_length=120, required=False, allow_blank=True)
    business_phone = serializers.CharField(max_length=40, required=False, allow_blank=True)
    supporting_url = serializers.URLField(required=False, allow_blank=True)
    evidence_notes = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    requested_level = serializers.ChoiceField(
        choices=[
            ManagedAgentProfile.VerificationLevel.BASIC,
            ManagedAgentProfile.VerificationLevel.BUSINESS,
            ManagedAgentProfile.VerificationLevel.ENHANCED,
        ],
        default=ManagedAgentProfile.VerificationLevel.BUSINESS,
    )
    development_code = serializers.CharField(max_length=6, required=False, allow_blank=True, write_only=True)

    def validate(self, attrs):
        method = attrs["method"]
        if method == "domain" and not attrs.get("domain", "").strip():
            raise serializers.ValidationError({"domain": "Enter the business domain."})
        if method == "manual":
            if not attrs.get("country", "").strip():
                raise serializers.ValidationError({"country": "Enter the country where the business operates."})
            if not attrs.get("business_phone", "").strip():
                raise serializers.ValidationError({"business_phone": "Enter a business phone number."})
            if not any(attrs.get(field, "").strip() for field in ("registration_number", "supporting_url", "evidence_notes")):
                raise serializers.ValidationError({"detail": "Provide a registration number, business profile URL, or review notes."})
        if method == "development" and not attrs.get("development_code", ""):
            raise serializers.ValidationError({"development_code": "Enter the local verification code."})
        return attrs


class SandboxInputSerializer(serializers.Serializer):
    prompt = serializers.CharField(max_length=4000)
