from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.profiles.models import UserProfile

from .models import Agent, AgentConnection, DataGrant, Task, TaskResult
from .services import provision_personal_agent


class AgenResolverFlowTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="task-owner")
        self.provider_owner = user_model.objects.create_user(username="provider-owner")
        self.intruder = user_model.objects.create_user(username="intruder")
        self.personal_agent, _ = provision_personal_agent(self.user, "Nova")
        self.provider = Agent.objects.create(
            owner=self.provider_owner,
            name="Lagos Table Agent",
            slug="lagos-table-agent",
            kind=Agent.Kind.BUSINESS,
            status=Agent.Status.ACTIVE,
            category="Hospitality",
            location="Lagos, Nigeria",
            endpoint="https://provider.example/agent",
            capabilities=["restaurant_search", "reservation"],
            verified=True,
            trust_score="91.0",
            trust_level=Agent.TrustLevel.HIGH_TRUST,
            online=True,
        )
        self.lower_match = Agent.objects.create(
            owner=self.intruder,
            name="General Booking Agent",
            slug="general-booking-agent",
            kind=Agent.Kind.BUSINESS,
            status=Agent.Status.ACTIVE,
            category="Bookings",
            location="Accra, Ghana",
            endpoint="https://booking.example/agent",
            capabilities=["reservation"],
            verified=True,
            trust_score="75.0",
            trust_level=Agent.TrustLevel.TRUSTED,
            online=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def discover(self, request_text="Find and reserve a restaurant in Lagos"):
        return self.client.post(
            "/api/resolver/discover/",
            {"request_text": request_text, "location": "Lagos"},
            format="json",
        )

    def test_discovery_creates_private_task_and_ranks_verified_agents(self):
        response = self.discover()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], Task.Status.AWAITING_APPROVAL)
        self.assertEqual(response.data["discovery_spec"]["capabilities"], ["restaurant_search", "reservation", "booking", "research"])
        self.assertEqual(response.data["candidates"][0]["network_handle"], self.provider.network_handle)
        self.assertGreater(response.data["candidates"][0]["match_score"], response.data["candidates"][1]["match_score"])
        task = Task.objects.get(task_id=response.data["task_id"])
        self.assertEqual(task.owner, self.user)
        self.assertEqual(task.request_text, "Find and reserve a restaurant in Lagos")

    def test_discovery_rejects_user_supplied_trust_scores(self):
        response = self.client.post(
            "/api/resolver/discover/",
            {"request_text": "Reserve a table", "trust_score": 100},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("trust_score", response.data)

    def test_tasks_are_invisible_to_other_users(self):
        created = self.discover()
        task_id = created.data["task_id"]
        self.client.force_authenticate(self.intruder)

        detail = self.client.get(f"/api/resolver/tasks/{task_id}/")
        task_list = self.client.get("/api/resolver/tasks/")

        self.assertEqual(detail.status_code, 404)
        self.assertEqual(task_list.status_code, 200)
        self.assertEqual(task_list.data, [])

    def test_pending_connection_hides_endpoint_until_owner_approves(self):
        task = self.discover().data
        connection_response = self.client.post(
            f"/api/resolver/tasks/{task['task_id']}/connect/",
            {"candidate_handle": self.provider.network_handle, "scopes": ["task_context", "location"]},
            format="json",
        )

        self.assertEqual(connection_response.status_code, 201)
        self.assertEqual(connection_response.data["status"], AgentConnection.Status.PENDING_APPROVAL)
        self.assertNotIn("endpoint", connection_response.data["provider"])
        self.assertIsNone(connection_response.data["data_grant"])

        approved = self.client.post(
            f"/api/resolver/connections/{connection_response.data['connection_id']}/approve/",
            {"scopes": ["task_context", "location"]},
            format="json",
        )
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.data["status"], AgentConnection.Status.APPROVED)
        self.assertEqual(approved.data["provider"]["endpoint"], self.provider.endpoint)
        self.assertEqual(approved.data["data_grant"]["scopes"], ["task_context", "location"])
        self.assertTrue(DataGrant.objects.get(grant_id=approved.data["data_grant"]["grant_id"]).active)

    def test_auto_connect_only_applies_to_low_risk_non_sensitive_tasks(self):
        UserProfile.objects.update_or_create(
            user=self.user,
            defaults={"approval_mode": UserProfile.ApprovalMode.AUTO_CONNECT},
        )
        task = self.discover("Reserve a restaurant in Lagos").data

        connected = self.client.post(
            f"/api/resolver/tasks/{task['task_id']}/connect/",
            {"candidate_handle": self.provider.network_handle, "scopes": ["task_context", "location"]},
            format="json",
        )

        self.assertEqual(connected.status_code, 201)
        self.assertTrue(connected.data["auto_approved"])
        self.assertEqual(connected.data["status"], AgentConnection.Status.APPROVED)
        self.assertIsNotNone(connected.data["data_grant"])

    def test_approval_cannot_escalate_requested_data_scopes(self):
        task = self.discover().data
        pending = self.client.post(
            f"/api/resolver/tasks/{task['task_id']}/connect/",
            {"candidate_handle": self.provider.network_handle, "scopes": ["task_context"]},
            format="json",
        ).data

        response = self.client.post(
            f"/api/resolver/connections/{pending['connection_id']}/approve/",
            {"scopes": ["task_context", "payment"]},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(DataGrant.objects.filter(connection__connection_id=pending["connection_id"]).exists())

    def test_sensitive_task_never_auto_connects(self):
        UserProfile.objects.update_or_create(
            user=self.user,
            defaults={"approval_mode": UserProfile.ApprovalMode.AUTO_CONNECT},
        )
        task = self.discover("Reserve a restaurant and pay for it").data

        connected = self.client.post(
            f"/api/resolver/tasks/{task['task_id']}/connect/",
            {"candidate_handle": self.provider.network_handle, "scopes": ["task_context", "payment"]},
            format="json",
        )

        self.assertEqual(connected.status_code, 201)
        self.assertFalse(connected.data["auto_approved"])
        self.assertEqual(connected.data["status"], AgentConnection.Status.PENDING_APPROVAL)

    def test_only_provider_owner_can_submit_result(self):
        task = self.discover().data
        pending = self.client.post(
            f"/api/resolver/tasks/{task['task_id']}/connect/",
            {"candidate_handle": self.provider.network_handle},
            format="json",
        ).data
        self.client.post(f"/api/resolver/connections/{pending['connection_id']}/approve/", {}, format="json")

        self.client.force_authenticate(self.intruder)
        rejected = self.client.post(
            f"/api/resolver/connections/{pending['connection_id']}/result/",
            {"summary": "Fake result"},
            format="json",
        )
        self.assertEqual(rejected.status_code, 404)

        self.client.force_authenticate(self.provider_owner)
        submitted = self.client.post(
            f"/api/resolver/connections/{pending['connection_id']}/result/",
            {"summary": "A table is reserved for 7 PM.", "structured_result": {"time": "19:00"}},
            format="json",
        )
        self.assertEqual(submitted.status_code, 201)
        self.assertEqual(submitted.data["summary"], "A table is reserved for 7 PM.")
        self.assertTrue(TaskResult.objects.filter(task__task_id=task["task_id"]).exists())
        self.assertEqual(Task.objects.get(task_id=task["task_id"]).status, Task.Status.COMPLETED)

    def test_provider_inbox_contains_only_granted_sanitized_context(self):
        task = self.discover("Reserve a Lagos table for ada@example.com or call +234 801 234 5678").data
        pending = self.client.post(
            f"/api/resolver/tasks/{task['task_id']}/connect/",
            {"candidate_handle": self.provider.network_handle, "scopes": ["task_context"]},
            format="json",
        ).data
        self.client.post(f"/api/resolver/connections/{pending['connection_id']}/approve/", {}, format="json")

        self.client.force_authenticate(self.provider_owner)
        inbox = self.client.get("/api/resolver/provider/connections/")

        self.assertEqual(inbox.status_code, 200)
        self.assertEqual(len(inbox.data), 1)
        task_spec = inbox.data[0]["task_spec"]
        self.assertIn("[email redacted]", task_spec["brief"])
        self.assertIn("[number redacted]", task_spec["brief"])
        self.assertNotIn("location", task_spec)
        self.assertNotIn("request_text", inbox.data[0])
