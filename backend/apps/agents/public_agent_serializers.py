from django.conf import settings
from rest_framework import serializers

from .models import AgentCatalogItem, PublicAgentProfile


class PublicProfileSettingsSerializer(serializers.ModelSerializer):
    canonical_url = serializers.SerializerMethodField()
    publishable = serializers.SerializerMethodField()
    publish_blockers = serializers.SerializerMethodField()
    published_source_ids = serializers.SerializerMethodField()
    published_item_ids = serializers.SerializerMethodField()

    class Meta:
        model = PublicAgentProfile
        fields = [
            "visibility", "tagline", "public_description", "logo_url", "cover_url", "website_url",
            "social_links", "published_capabilities", "languages", "public_location", "public_chat_enabled",
            "guest_daily_limit", "show_catalog", "show_trust_history", "canonical_url",
            "publishable", "publish_blockers", "published_source_ids", "published_item_ids", "updated_at",
        ]

    def get_canonical_url(self, obj):
        return f"{settings.FRONTEND_PUBLIC_URL}/agents/{obj.agent.network_handle}"

    def get_publishable(self, obj):
        return not self.get_publish_blockers(obj)

    def get_publish_blockers(self, obj):
        blockers = []
        if not obj.agent.verified:
            blockers.append("Complete business verification before publishing this agent.")
        if obj.agent.status != obj.agent.Status.ACTIVE:
            blockers.append("Activate this agent before publishing its profile.")
        return blockers

    def get_published_source_ids(self, obj):
        return [str(value) for value in obj.agent.knowledge_sources.filter(published=True).values_list("source_id", flat=True)]

    def get_published_item_ids(self, obj):
        return [str(value) for value in obj.agent.catalog_items.filter(published=True).values_list("item_id", flat=True)]


class PublicProfileInputSerializer(serializers.ModelSerializer):
    published_source_ids = serializers.ListField(child=serializers.UUIDField(), required=False, max_length=100)
    published_item_ids = serializers.ListField(child=serializers.UUIDField(), required=False, max_length=500)

    class Meta:
        model = PublicAgentProfile
        fields = [
            "visibility", "tagline", "public_description", "logo_url", "cover_url", "website_url",
            "social_links", "published_capabilities", "languages", "public_location", "public_chat_enabled",
            "guest_daily_limit", "show_catalog", "show_trust_history", "published_source_ids", "published_item_ids",
        ]
        extra_kwargs = {
            "social_links": {"required": False},
            "published_capabilities": {"required": False},
            "languages": {"required": False},
        }

    def validate_guest_daily_limit(self, value):
        if value < 1 or value > 500:
            raise serializers.ValidationError("Guest daily limit must be between 1 and 500.")
        return value

    def validate_social_links(self, value):
        if not isinstance(value, list) or len(value) > 8:
            raise serializers.ValidationError("Provide up to eight social links.")
        for link in value:
            if not isinstance(link, dict) or set(link) - {"label", "url"} or not link.get("label") or not str(link.get("url", "")).startswith("https://"):
                raise serializers.ValidationError("Each social link requires a label and HTTPS URL.")
        return value


class PublicCatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentCatalogItem
        fields = ["item_id", "name", "sku", "description", "price", "currency", "availability"]


class GuestChatInputSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000)
    session_id = serializers.UUIDField(required=False)
