from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .conversation_crypto import decrypt_message
from .models import Agent, AgentKnowledgeSource, AgentToolConnection
from .services import register_business_agent


class ManagedBusinessAgentTests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.owner = users.objects.create_user(username="owner@acme.test", email="owner@acme.test")
        self.other = users.objects.create_user(username="other@example.test", email="other@example.test")
        self.agent = register_business_agent(self.owner, {
            "name": "Acme Guide",
            "company_name": "Acme Ltd",
            "category": "Customer support",
            "hosting_type": Agent.HostingType.MANAGED,
            "summary": "Answers customer questions.",
            "capabilities": [],
        })
        self.client = APIClient()
        self.client.force_authenticate(self.owner)
        self.base = f"/api/agents/business/{self.agent.agent_id}"

    def test_setup_is_private_and_only_available_for_managed_agents(self):
        self.assertEqual(self.client.get(f"{self.base}/setup/").status_code, 200)

        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(f"{self.base}/setup/").status_code, 404)
        self.assertEqual(self.client.post(f"{self.base}/knowledge/", {"title": "Stolen", "content": "No"}).status_code, 404)

    def test_template_seeds_capabilities_instructions_and_knowledge(self):
        response = self.client.post(f"{self.base}/template/customer_support/", {}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["profile"]["template_key"], "customer_support")
        self.assertIn("customer_support", response.data["agent"]["capabilities"])
        self.assertTrue(response.data["profile"]["instructions"])
        self.assertGreaterEqual(len(response.data["knowledge"]), 1)

    def test_knowledge_and_tool_secrets_are_encrypted_and_not_returned(self):
        knowledge = self.client.post(
            f"{self.base}/knowledge/",
            {"kind": "faq", "title": "Returns", "content": "Returns are accepted within seven days."},
            format="json",
        )
        tool = self.client.post(
            f"{self.base}/tools/",
            {
                "provider": "shop_api",
                "display_name": "Shop API",
                "scopes": ["inventory_read"],
                "secret_config": {"api_key": "super-secret-key"},
            },
            format="json",
        )

        self.assertEqual(knowledge.status_code, 201)
        stored = AgentKnowledgeSource.objects.get(source_id=knowledge.data["source_id"])
        self.assertNotIn("seven days", stored.content_ciphertext)
        self.assertIn("seven days", decrypt_message(stored.content_ciphertext))
        self.assertEqual(tool.status_code, 201)
        self.assertTrue(tool.data["has_secret_config"])
        self.assertNotIn("secret_config", tool.data)
        self.assertNotIn("super-secret-key", AgentToolConnection.objects.get(connection_id=tool.data["connection_id"]).config_ciphertext)

    def test_activation_requires_verified_complete_and_tested_setup(self):
        rejected = self.client.post(f"{self.base}/activate/", {}, format="json")
        self.assertEqual(rejected.status_code, 400)
        self.assertIn("business_verified", rejected.data["missing"])

        self.client.post(f"{self.base}/template/customer_support/", {}, format="json")
        verification = self.client.post(f"{self.base}/verification/", {"method": "domain", "domain": "acme.test"}, format="json")
        sandbox = self.client.post(
            f"{self.base}/sandbox/",
            {"prompt": "When should support escalation happen?"},
            format="json",
        )
        activated = self.client.post(f"{self.base}/activate/", {}, format="json")

        self.assertEqual(verification.data["profile"]["verification_status"], "verified")
        self.assertEqual(sandbox.status_code, 201)
        self.assertEqual(sandbox.data["status"], "passed")
        self.assertEqual(activated.status_code, 200)
        self.assertEqual(activated.data["agent"]["status"], Agent.Status.ACTIVE)
        self.agent.refresh_from_db()
        self.assertTrue(self.agent.verified)
        self.assertEqual(self.agent.status, Agent.Status.ACTIVE)

    def test_unmatched_email_domain_stays_pending(self):
        response = self.client.post(f"{self.base}/verification/", {"method": "domain", "domain": "different.test"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["profile"]["verification_status"], "pending")
        self.agent.refresh_from_db()
        self.assertFalse(self.agent.verified)

    def test_business_without_website_can_submit_manual_review(self):
        response = self.client.post(
            f"{self.base}/verification/",
            {
                "method": "manual",
                "requested_level": "basic",
                "country": "Nigeria",
                "business_phone": "+2348012345678",
                "supporting_url": "https://instagram.com/acme-store",
                "evidence_notes": "We trade through our social storefront.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["profile"]["verification_status"], "pending")
        self.assertEqual(response.data["profile"]["verification_method"], "manual_review")
        self.assertEqual(response.data["profile"]["requested_verification_level"], "basic")

    @override_settings(DEBUG=True, BUSINESS_DEV_VERIFICATION_CODE="246810")
    def test_development_code_can_verify_any_level_locally(self):
        response = self.client.post(
            f"{self.base}/verification/",
            {"method": "development", "development_code": "246810", "requested_level": "enhanced"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["profile"]["verification_status"], "verified")
        self.assertEqual(response.data["profile"]["verification_level"], "enhanced")
        self.assertEqual(response.data["profile"]["verification_method"], "development")

    @override_settings(DEBUG=False, BUSINESS_DEV_VERIFICATION_CODE="")
    def test_development_verification_is_unavailable_in_production(self):
        response = self.client.post(
            f"{self.base}/verification/",
            {"method": "development", "development_code": "246810", "requested_level": "enhanced"},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

    @override_settings(DEBUG=True, BUSINESS_DEV_VERIFICATION_CODE="246810")
    def test_sensitive_actions_require_enhanced_verification(self):
        self.client.patch(
            f"{self.base}/setup/",
            {"allowed_actions": ["issue_refund"]},
            format="json",
        )
        verified = self.client.post(
            f"{self.base}/verification/",
            {"method": "development", "development_code": "246810", "requested_level": "business"},
            format="json",
        )

        self.assertEqual(verified.data["readiness"]["required_verification_level"], "enhanced")
        self.assertFalse(verified.data["readiness"]["checks"]["business_verified"])
