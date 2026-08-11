from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .conversation_crypto import decrypt_message
from .conversation_services import purge_expired_conversations
from .models import Conversation, ConversationMessage, Task
from .services import provision_personal_agent


@override_settings(AGENT_LLM_PROVIDER="disabled", OPENAI_API_KEY="")
class ConversationApiTests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.user = users.objects.create_user(username="conversation-owner")
        self.other = users.objects.create_user(username="another-owner")
        provision_personal_agent(self.user, "Cody")
        provision_personal_agent(self.other, "Nova")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def create_conversation(self, **data):
        return self.client.post("/api/conversations/", data, format="json")

    def test_message_is_encrypted_linked_to_task_and_restored_on_reload(self):
        created = self.create_conversation()
        conversation_id = created.data["conversation_id"]

        sent = self.client.post(
            f"/api/conversations/{conversation_id}/messages/",
            {"content": "Plan a private launch for Friday"},
            format="json",
        )

        self.assertEqual(sent.status_code, 201)
        self.assertEqual(sent.data["user_message"]["content"], "Plan a private launch for Friday")
        self.assertTrue(sent.data["agent_message"]["task_id"])
        stored = ConversationMessage.objects.get(message_id=sent.data["user_message"]["message_id"])
        self.assertNotIn("private launch", stored.content_ciphertext)
        self.assertEqual(decrypt_message(stored.content_ciphertext), "Plan a private launch for Friday")
        self.assertTrue(Task.objects.filter(task_id=sent.data["task"]["task_id"]).exists())

        reloaded = self.client.get(f"/api/conversations/{conversation_id}/")
        self.assertEqual([message["role"] for message in reloaded.data["messages"]], ["user", "agent"])
        self.assertEqual(reloaded.data["messages"][0]["content"], "Plan a private launch for Friday")

    def test_conversations_are_private_to_the_owner(self):
        conversation_id = self.create_conversation().data["conversation_id"]
        self.client.force_authenticate(self.other)

        self.assertEqual(self.client.get(f"/api/conversations/{conversation_id}/").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/conversations/{conversation_id}/").status_code, 404)
        self.assertEqual(self.client.get("/api/conversations/").data, [])

    def test_archived_conversation_rejects_new_messages_and_can_be_deleted(self):
        conversation_id = self.create_conversation().data["conversation_id"]
        archived = self.client.patch(
            f"/api/conversations/{conversation_id}/",
            {"status": Conversation.Status.ARCHIVED},
            format="json",
        )
        rejected = self.client.post(
            f"/api/conversations/{conversation_id}/messages/",
            {"content": "This should not be stored"},
            format="json",
        )

        self.assertEqual(archived.status_code, 200)
        self.assertEqual(rejected.status_code, 404)
        self.assertEqual(self.client.delete(f"/api/conversations/{conversation_id}/").status_code, 204)
        self.assertFalse(Conversation.objects.filter(conversation_id=conversation_id).exists())

    def test_expired_conversations_are_purged(self):
        conversation_id = self.create_conversation(retention_policy="30_days").data["conversation_id"]
        Conversation.objects.filter(conversation_id=conversation_id).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )

        purge_expired_conversations(self.user)

        self.assertFalse(Conversation.objects.filter(conversation_id=conversation_id).exists())

    def test_session_conversations_are_deleted_on_logout(self):
        conversation_id = self.create_conversation(retention_policy="session").data["conversation_id"]

        response = self.client.post("/api/auth/logout/", {}, format="json")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Conversation.objects.filter(conversation_id=conversation_id).exists())
