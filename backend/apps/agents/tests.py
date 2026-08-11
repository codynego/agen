from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Agent, AgentActivity, TrustEvent


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
        self.assertNotIn("endpoint", response.data)
        self.assertNotIn("allowed_actions", response.data)
        self.assertNotIn("blocked_actions", response.data)
        self.assertNotIn("activities", response.data)

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


class PrivateAgentIsolationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(username="owner", password="test-password")
        self.other_user = user_model.objects.create_user(username="other", password="test-password")
        self.owner_agent = Agent.objects.create(
            owner=self.owner,
            name="Owner Agen",
            slug="owner-agen",
            kind=Agent.Kind.PERSONAL,
            status=Agent.Status.ACTIVE,
            category="Personal assistant",
            endpoint="https://private.owner.test/run",
            allowed_actions=["read_owner_calendar"],
        )
        self.other_agent = Agent.objects.create(
            owner=self.other_user,
            name="Other Agen",
            slug="other-agen",
            kind=Agent.Kind.PERSONAL,
            status=Agent.Status.ACTIVE,
            category="Personal assistant",
            endpoint="https://private.other.test/run",
            allowed_actions=["read_other_calendar"],
        )
        AgentActivity.objects.create(agent=self.owner_agent, title="Owner task", detail="Private owner activity")
        AgentActivity.objects.create(agent=self.other_agent, title="Other task", detail="Private other activity")
        self.client = APIClient()

    def test_private_agent_endpoints_require_authentication(self):
        self.assertEqual(self.client.get("/api/agents/").status_code, 403)
        self.assertEqual(self.client.get("/api/dashboard/").status_code, 403)
        self.assertEqual(self.client.get(f"/api/agents/{self.owner_agent.slug}/").status_code, 403)

    def test_agent_list_only_returns_agents_owned_by_current_user(self):
        self.client.force_authenticate(self.owner)

        response = self.client.get("/api/agents/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["agent_id"] for item in response.data], [str(self.owner_agent.agent_id)])
        self.assertEqual(response.data[0]["endpoint"], "https://private.owner.test/run")

    def test_agent_detail_hides_agents_owned_by_another_user(self):
        self.client.force_authenticate(self.owner)

        own_response = self.client.get(f"/api/agents/{self.owner_agent.slug}/")
        other_response = self.client.get(f"/api/agents/{self.other_agent.slug}/")

        self.assertEqual(own_response.status_code, 200)
        self.assertEqual(other_response.status_code, 404)

    def test_dashboard_only_uses_current_users_agents_and_activity(self):
        self.client.force_authenticate(self.owner)

        response = self.client.get("/api/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["personal_agent"]["agent_id"], str(self.owner_agent.agent_id))
        self.assertEqual(response.data["metrics"]["my_agents"], 1)
        self.assertEqual(response.data["metrics"]["network_requests"], 1)
        self.assertEqual(len(response.data["recent_activity"]), 1)
        self.assertEqual(response.data["recent_activity"][0]["title"], "Owner task")
        self.assertNotContains(response, "Private other activity")

    def test_public_verification_exposes_identity_but_not_private_configuration(self):
        response = self.client.get(f"/api/agents/verify/{self.owner_agent.agent_id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["agent_id"], str(self.owner_agent.agent_id))
        self.assertNotIn("endpoint", response.data)
        self.assertNotIn("allowed_actions", response.data)
        self.assertNotIn("activities", response.data)


class AgentNetworkHandleTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.first_user = user_model.objects.create_user(username="first-handle-owner")
        self.second_user = user_model.objects.create_user(username="second-handle-owner")

    def create_agent(self, owner, slug):
        return Agent.objects.create(
            owner=owner,
            name="Nova",
            slug=slug,
            kind=Agent.Kind.PERSONAL,
            status=Agent.Status.ACTIVE,
            category="Personal assistant",
        )

    def test_duplicate_names_receive_different_network_handles(self):
        first = self.create_agent(self.first_user, "first-nova")
        second = self.create_agent(self.second_user, "second-nova")

        self.assertEqual(first.name, second.name)
        self.assertNotEqual(first.network_handle, second.network_handle)
        self.assertTrue(first.network_handle.startswith("agen-"))
        self.assertTrue(second.network_handle.startswith("agen-"))

    def test_network_handle_cannot_be_changed_after_creation(self):
        agent = self.create_agent(self.first_user, "immutable-nova")
        original_handle = agent.network_handle

        agent.network_handle = "changed-by-user"
        agent.save()
        agent.refresh_from_db()

        self.assertEqual(agent.network_handle, original_handle)

    def test_active_agent_can_be_verified_by_network_handle(self):
        agent = self.create_agent(self.first_user, "public-nova")

        response = APIClient().get(f"/api/agents/handle/{agent.network_handle}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["agent_id"], str(agent.agent_id))
        self.assertEqual(response.data["network_handle"], agent.network_handle)
