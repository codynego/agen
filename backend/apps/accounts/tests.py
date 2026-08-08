from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.agents.models import Agent


class SessionAuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)

    def csrf_token(self):
        response = self.client.get("/api/auth/csrf/")
        return response.data["csrf_token"]

    def test_registration_creates_session_and_personal_agent(self):
        response = self.client.post(
            "/api/auth/register/",
            {"name": "Ada Lovelace", "email": "ada@example.com", "password": "Complex-pass-924"},
            format="json",
            HTTP_X_CSRFTOKEN=self.csrf_token(),
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["user"]["email"], "ada@example.com")
        self.assertEqual(response.data["personal_agent"]["kind"], Agent.Kind.PERSONAL)
        self.assertTrue(get_user_model().objects.filter(email="ada@example.com").exists())
        self.assertEqual(Agent.objects.filter(owner__email="ada@example.com", kind=Agent.Kind.PERSONAL).count(), 1)
        self.assertIn("sessionid", self.client.cookies)

    def test_login_me_and_logout_lifecycle(self):
        get_user_model().objects.create_user(
            username="grace@example.com",
            email="grace@example.com",
            password="Complex-pass-924",
        )
        login_response = self.client.post(
            "/api/auth/login/",
            {"email": "grace@example.com", "password": "Complex-pass-924"},
            format="json",
            HTTP_X_CSRFTOKEN=self.csrf_token(),
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 200)

        logout_response = self.client.post(
            "/api/auth/logout/",
            {},
            format="json",
            HTTP_X_CSRFTOKEN=self.csrf_token(),
        )
        self.assertEqual(logout_response.status_code, 204)
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 403)

    def test_registration_requires_csrf(self):
        response = self.client.post(
            "/api/auth/register/",
            {"name": "No Token", "email": "no-token@example.com", "password": "Complex-pass-924"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
