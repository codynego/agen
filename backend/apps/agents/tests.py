from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Agent, TrustEvent


class PersonalAgentProvisionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="ada", password="test-password")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_provisioning_is_idempotent_and_assigns_public_identity(self):
        first = self.client.post("/api/agents/personal/provision/", {"name": "Ada's Agen"}, format="json")
        second = self.client.post("/api/agents/personal/provision/", {"name": "Another name"}, format="json")

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data["agent_id"], second.data["agent_id"])
        self.assertEqual(Agent.objects.filter(owner=self.user, kind=Agent.Kind.PERSONAL).count(), 1)
        self.assertEqual(first.data["trust_score"], "40.0")

    def test_public_verification_excludes_owner_data_and_reflects_trust_events(self):
        provisioned = self.client.post("/api/agents/personal/provision/", {}, format="json")
        agent = Agent.objects.get(agent_id=provisioned.data["agent_id"])
        TrustEvent.objects.create(
            subject_agent=agent,
            category=TrustEvent.Category.TASK_COMPLETED,
            outcome=TrustEvent.Outcome.POSITIVE,
            score_delta="5.0",
            evidence_hash="a" * 64,
        )

        self.client.force_authenticate(user=None)
        response = self.client.get(f"/api/agents/verify/{agent.agent_id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["agent_id"], str(agent.agent_id))
        self.assertEqual(response.data["trust_score"], "45.0")
        self.assertEqual(response.data["trust_event_count"], 1)
        self.assertNotIn("owner", response.data)
        self.assertNotIn("location", response.data)

    def test_public_trust_history_is_available_by_agent_id(self):
        provisioned = self.client.post("/api/agents/personal/provision/", {}, format="json")
        agent = Agent.objects.get(agent_id=provisioned.data["agent_id"])
        event = TrustEvent.objects.create(
            subject_agent=agent,
            category=TrustEvent.Category.PEER_ATTESTATION,
            outcome=TrustEvent.Outcome.POSITIVE,
            score_delta="3.0",
        )

        self.client.force_authenticate(user=None)
        response = self.client.get(f"/api/agents/verify/{agent.agent_id}/trust/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["event_id"], str(event.event_id))


class BusinessAgentRegistrationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="business-owner", password="test-password")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_managed_business_agent_gets_independent_draft_identity(self):
        response = self.client.post(
            "/api/agents/business/",
            {
                "name": "Acme Support",
                "company_name": "Acme Ltd",
                "category": "Customer support",
                "hosting_type": "managed",
                "summary": "Handles customer questions.",
                "capabilities": ["support", "order_status"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["kind"], Agent.Kind.BUSINESS)
        self.assertEqual(response.data["hosting_type"], Agent.HostingType.MANAGED)
        self.assertEqual(response.data["status"], Agent.Status.DRAFT)
        self.assertEqual(response.data["trust_score"], "40.0")

    def test_external_agent_requires_https_endpoint(self):
        response = self.client.post(
            "/api/agents/business/",
            {
                "name": "Acme External",
                "company_name": "Acme Ltd",
                "category": "Commerce",
                "hosting_type": "external",
                "endpoint": "http://agents.acme.test/run",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("endpoint", response.data)
