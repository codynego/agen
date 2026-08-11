from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .conversation_crypto import decrypt_message, encrypt_message
from .models import (
    Agent,
    AgentCatalogItem,
    AgentKnowledgeSource,
    GuestAgentMessage,
    ManagedAgentProfile,
    PublicAgentProfile,
)


@override_settings(FRONTEND_PUBLIC_URL="https://agen.example", AGENT_LLM_PROVIDER="disabled")
class PublicBusinessAgentTests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.owner = users.objects.create_user(username="public-owner", email="owner@acme.test")
        self.other = users.objects.create_user(username="other-public-owner")
        self.agent = Agent.objects.create(
            owner=self.owner,
            name="Acme Guide",
            slug="acme-guide-public",
            kind=Agent.Kind.BUSINESS,
            hosting_type=Agent.HostingType.MANAGED,
            status=Agent.Status.ACTIVE,
            category="Commerce",
            company_name="Acme Ltd",
            summary="Private fallback summary",
            verified=True,
            online=True,
            capabilities=["product_search", "order_status", "private_admin"],
        )
        ManagedAgentProfile.objects.create(
            agent=self.agent,
            verification_status=ManagedAgentProfile.VerificationStatus.VERIFIED,
            verification_level=ManagedAgentProfile.VerificationLevel.BUSINESS,
        )
        self.profile = PublicAgentProfile.objects.create(
            agent=self.agent,
            visibility=PublicAgentProfile.Visibility.PRIVATE,
            tagline="Find the right essentials",
            public_description="A public business description.",
            published_capabilities=["product_search"],
            public_chat_enabled=True,
            guest_daily_limit=1,
        )
        self.published_knowledge = AgentKnowledgeSource.objects.create(
            agent=self.agent,
            kind=AgentKnowledgeSource.Kind.FAQ,
            title="Returns",
            content_ciphertext=encrypt_message("Unused products can be returned within seven days."),
            published=True,
        )
        AgentKnowledgeSource.objects.create(
            agent=self.agent,
            title="Internal escalation",
            content_ciphertext=encrypt_message("Private manager phone is 555-0100."),
            published=False,
        )
        self.item = AgentCatalogItem.objects.create(
            agent=self.agent,
            name="Skincare Set",
            sku="SKIN-01",
            description="Cleanser, moisturizer, and sunscreen.",
            price="18500",
            currency="NGN",
            published=True,
        )
        AgentCatalogItem.objects.create(agent=self.agent, name="Internal Item", published=False)
        self.public_url = f"/api/public/agents/{self.agent.network_handle}/"
        self.owner_url = f"/api/agents/business/{self.agent.agent_id}/public-profile/"
        self.client = APIClient()

    def test_private_profile_is_not_public(self):
        self.assertEqual(self.client.get(self.public_url).status_code, 404)

    def test_owner_can_publish_but_other_users_cannot_edit(self):
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.patch(self.owner_url, {"visibility": "public"}, format="json").status_code, 404)

        self.client.force_authenticate(self.owner)
        response = self.client.patch(
            self.owner_url,
            {
                "visibility": "public",
                "published_capabilities": ["product_search"],
                "published_source_ids": [str(self.published_knowledge.source_id)],
                "published_item_ids": [str(self.item.item_id)],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["canonical_url"], f"https://agen.example/agents/{self.agent.network_handle}")
        self.assertTrue(response.data["publishable"])
        self.assertEqual(response.data["publish_blockers"], [])

    def test_unverified_agent_cannot_be_published(self):
        self.agent.verified = False
        self.agent.save(update_fields=["verified", "updated_at"])
        self.client.force_authenticate(self.owner)

        response = self.client.patch(self.owner_url, {"visibility": "public"}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("verification", response.data["visibility"][0].lower())
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.visibility, PublicAgentProfile.Visibility.PRIVATE)

    def test_public_profile_and_manifest_exclude_private_configuration(self):
        self.profile.visibility = PublicAgentProfile.Visibility.PUBLIC
        self.profile.save()

        response = self.client.get(self.public_url)
        manifest = self.client.get(f"{self.public_url}manifest/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["capabilities"], ["product_search"])
        self.assertEqual([item["name"] for item in response.data["catalog"]], ["Skincare Set"])
        self.assertNotContains(response, "Internal Item")
        self.assertNotContains(response, "Private manager")
        self.assertNotIn("instructions", response.data)
        self.assertNotIn("allowed_actions", response.data)
        self.assertEqual(manifest.data["protocol"], "agen-v1")

    def test_guest_chat_uses_only_published_sources_encrypts_logs_and_rate_limits(self):
        self.profile.visibility = PublicAgentProfile.Visibility.PUBLIC
        self.profile.save()

        response = self.client.post(
            f"{self.public_url}chat/",
            {"message": "Can I return an unused product?"},
            format="json",
            REMOTE_ADDR="203.0.113.10",
        )
        limited = self.client.post(
            f"{self.public_url}chat/",
            {"message": "What is the manager phone?"},
            format="json",
            REMOTE_ADDR="203.0.113.10",
        )

        self.assertEqual(response.status_code, 201)
        self.assertIn("seven days", response.data["response"])
        self.assertNotIn("555-0100", response.data["response"])
        stored = GuestAgentMessage.objects.get(message_id=response.data["message_id"])
        self.assertNotIn("unused product", stored.prompt_ciphertext)
        self.assertIn("unused product", decrypt_message(stored.prompt_ciphertext).lower())
        self.assertEqual(limited.status_code, 429)

    def test_guest_chat_without_a_match_responds_naturally_without_inventing(self):
        self.profile.visibility = PublicAgentProfile.Visibility.PUBLIC
        self.profile.guest_daily_limit = 2
        self.profile.save()

        response = self.client.post(
            f"{self.public_url}chat/",
            {"message": "Can you repair my laptop?"},
            format="json",
            REMOTE_ADDR="203.0.113.11",
        )

        self.assertEqual(response.status_code, 201)
        self.assertIn("Acme Ltd", response.data["response"])
        self.assertIn("don't have enough information", response.data["response"])
        self.assertNotIn("could not find a published answer", response.data["response"])

    def test_qr_endpoint_returns_svg(self):
        self.profile.visibility = PublicAgentProfile.Visibility.UNLISTED
        self.profile.save()

        response = self.client.get(f"{self.public_url}qr/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/svg+xml")
        self.assertIn(b"<svg", response.content)
