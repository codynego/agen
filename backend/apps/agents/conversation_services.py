from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from .conversation_crypto import encrypt_message
from .models import Conversation, ConversationMessage


def retention_expiry(policy: str):
    if policy == Conversation.RetentionPolicy.THIRTY_DAYS:
        return timezone.now() + timedelta(days=30)
    return None


def purge_expired_conversations(user) -> int:
    deleted, _ = Conversation.objects.filter(
        owner=user,
        expires_at__isnull=False,
        expires_at__lte=timezone.now(),
    ).delete()
    return deleted


@transaction.atomic
def append_message(conversation: Conversation, role: str, content: str, task=None) -> ConversationMessage:
    locked = Conversation.objects.select_for_update().get(pk=conversation.pk)
    sequence = (locked.messages.aggregate(value=Max("sequence"))["value"] or 0) + 1
    message = ConversationMessage.objects.create(
        conversation=locked,
        task=task,
        role=role,
        sequence=sequence,
        content_ciphertext=encrypt_message(content),
    )
    now = timezone.now()
    locked.last_message_at = now
    if locked.retention_policy == Conversation.RetentionPolicy.THIRTY_DAYS:
        locked.expires_at = now + timedelta(days=30)
    locked.save(update_fields=["last_message_at", "expires_at", "updated_at"])
    return message
