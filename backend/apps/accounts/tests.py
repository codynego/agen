import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.agents.models import Agent

from .models import EmailLoginChallenge


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class EmailCodeAuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)

    def csrf_token(self):
        response = self.client.get("/api/auth/csrf/")
        return response.data["csrf_token"]

    def request_code(self, email="ada@example.com", name="Ada Lovelace"):
        response = self.client.post(
            "/api/auth/request-code/",
            {"email": email, "name": name},
            format="json",
            HTTP_X_CSRFTOKEN=self.csrf_token(),
        )
        code = re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1) if response.status_code == 200 else None
        return response, code

    def verify_code(self, challenge_id, code):
        return self.client.post(
            "/api/auth/verify-code/",
            {"challenge_id": str(challenge_id), "code": code},
            format="json",
            HTTP_X_CSRFTOKEN=self.csrf_token(),
        )

    def test_first_verification_creates_session_and_personal_agent(self):
        requested, code = self.request_code()
        response = self.verify_code(requested.data["challenge_id"], code)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["email"], "ada@example.com")
        self.assertEqual(response.data["personal_agent"]["kind"], Agent.Kind.PERSONAL)
        self.assertFalse(get_user_model().objects.get(email="ada@example.com").has_usable_password())
        self.assertEqual(Agent.objects.filter(owner__email="ada@example.com", kind=Agent.Kind.PERSONAL).count(), 1)
        self.assertIn("sessionid", self.client.cookies)

    def test_returning_user_reuses_account_and_agent(self):
        first_request, first_code = self.request_code()
        self.verify_code(first_request.data["challenge_id"], first_code)
        self.client.post("/api/auth/logout/", {}, format="json", HTTP_X_CSRFTOKEN=self.csrf_token())

        second_request, second_code = self.request_code(name="")
        response = self.verify_code(second_request.data["challenge_id"], second_code)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_user_model().objects.filter(email="ada@example.com").count(), 1)
        self.assertEqual(Agent.objects.filter(owner__email="ada@example.com", kind=Agent.Kind.PERSONAL).count(), 1)

    def test_code_is_single_use(self):
        requested, code = self.request_code()
        self.assertEqual(self.verify_code(requested.data["challenge_id"], code).status_code, 200)
        self.assertEqual(self.verify_code(requested.data["challenge_id"], code).status_code, 400)

    def test_expired_code_is_rejected(self):
        requested, code = self.request_code()
        EmailLoginChallenge.objects.filter(challenge_id=requested.data["challenge_id"]).update(
            expires_at=timezone.now() - timedelta(seconds=1),
        )
        self.assertEqual(self.verify_code(requested.data["challenge_id"], code).status_code, 400)

    def test_challenge_locks_after_five_incorrect_attempts(self):
        requested, correct_code = self.request_code()
        for _ in range(5):
            self.assertEqual(self.verify_code(requested.data["challenge_id"], "000000").status_code, 400)
        self.assertEqual(self.verify_code(requested.data["challenge_id"], correct_code).status_code, 400)

    def test_requesting_code_requires_csrf(self):
        response = self.client.post(
            "/api/auth/request-code/",
            {"email": "no-token@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    @override_settings(DEBUG=True, AUTH_DEV_LOGIN_CODE="123456")
    def test_fixed_development_code_can_authenticate(self):
        requested, emailed_code = self.request_code(email="developer@example.com")

        self.assertEqual(emailed_code, "123456")
        self.assertEqual(self.verify_code(requested.data["challenge_id"], "123456").status_code, 200)

    def test_logout_ends_authenticated_session(self):
        requested, code = self.request_code()
        self.verify_code(requested.data["challenge_id"], code)
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 200)

        response = self.client.post(
            "/api/auth/logout/",
            {},
            format="json",
            HTTP_X_CSRFTOKEN=self.csrf_token(),
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 403)
