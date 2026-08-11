from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.agents.models import Agent

from .models import UserProfile


class OnboardingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="new-user", email="new@example.com")
        self.client = APIClient()

    def payload(self, **overrides):
        data = {
            "agent_name": "Nova",
            "goals": ["work", "travel"],
            "approval_mode": UserProfile.ApprovalMode.BALANCED,
            "integrations": ["email_calendar", "files"],
        }
        data.update(overrides)
        return data

    def test_onboarding_requires_authentication(self):
        self.assertEqual(self.client.get("/api/profile/onboarding/").status_code, 403)
        self.assertEqual(self.client.post("/api/profile/onboarding/", self.payload(), format="json").status_code, 403)

    def test_onboarding_configures_only_the_authenticated_users_agent(self):
        other_user = get_user_model().objects.create_user(username="other-user")
        other_agent = Agent.objects.create(
            owner=other_user,
            name="Other Agen",
            slug="other-personal",
            kind=Agent.Kind.PERSONAL,
            category="Personal assistant",
        )
        self.client.force_authenticate(self.user)

        response = self.client.post("/api/profile/onboarding/", self.payload(), format="json")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["onboarding_completed"])
        self.assertEqual(response.data["agent_name"], "Nova")
        self.assertTrue(response.data["network_handle"].startswith("agen-"))
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.goal_categories, ["work", "travel"])
        self.assertEqual(profile.integration_interests, ["email_calendar", "files"])
        self.assertEqual(profile.approval_mode, UserProfile.ApprovalMode.BALANCED)
        other_agent.refresh_from_db()
        self.assertEqual(other_agent.name, "Other Agen")

    def test_user_cannot_set_or_change_agent_trust_score(self):
        self.client.force_authenticate(self.user)
        agent = Agent.objects.create(
            owner=self.user,
            name="New user's Agen",
            slug="new-user-personal",
            kind=Agent.Kind.PERSONAL,
            category="Personal assistant",
            trust_score="40.0",
        )

        response = self.client.post("/api/profile/onboarding/", self.payload(trust_score="100.0"), format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("trust_score", response.data)
        agent.refresh_from_db()
        self.assertEqual(str(agent.trust_score), "40.0")

    def test_onboarding_status_reports_network_managed_trust_as_read_only(self):
        self.client.force_authenticate(self.user)

        response = self.client.get("/api/profile/onboarding/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["onboarding_completed"])
        self.assertEqual(response.data["trust_score"], "40.0")
