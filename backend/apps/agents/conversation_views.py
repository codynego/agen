from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .conversation_serializers import (
    ConversationCreateSerializer,
    ConversationDetailSerializer,
    ConversationMessageSerializer,
    ConversationSendSerializer,
    ConversationSerializer,
    ConversationUpdateSerializer,
    MessageInputSerializer,
)
from .conversation_services import append_message, purge_expired_conversations, retention_expiry
from .models import Agent, Conversation, ConversationMessage, Task
from .resolver import discover_agents


def owner_conversations(user):
    return Conversation.objects.filter(owner=user).select_related("agent")


def conversation_list(user):
    latest = ConversationMessage.objects.order_by("-sequence")
    return owner_conversations(user).annotate(message_count=Count("messages")).prefetch_related(
        Prefetch("messages", queryset=latest, to_attr="latest_messages")
    )


class ConversationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        purge_expired_conversations(request.user)
        return Response(ConversationSerializer(conversation_list(request.user), many=True).data)

    def post(self, request):
        serializer = ConversationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        agent = get_object_or_404(Agent, owner=request.user, kind=Agent.Kind.PERSONAL)
        policy = serializer.validated_data["retention_policy"]
        conversation = Conversation.objects.create(
            owner=request.user,
            agent=agent,
            title=serializer.validated_data["title"].strip() or "New conversation",
            retention_policy=policy,
            expires_at=retention_expiry(policy),
        )
        conversation.message_count = 0
        conversation.latest_messages = []
        return Response(ConversationSerializer(conversation).data, status=status.HTTP_201_CREATED)


class ConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, user, conversation_id):
        purge_expired_conversations(user)
        return get_object_or_404(
            owner_conversations(user).prefetch_related("messages__task"),
            conversation_id=conversation_id,
        )

    def get(self, request, conversation_id):
        conversation = self.get_object(request.user, conversation_id)
        conversation.message_count = conversation.messages.count()
        conversation.latest_messages = list(conversation.messages.order_by("-sequence")[:1])
        return Response(ConversationDetailSerializer(conversation).data)

    def patch(self, request, conversation_id):
        conversation = self.get_object(request.user, conversation_id)
        serializer = ConversationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        if "title" in values:
            conversation.title = values["title"].strip() or "New conversation"
        if "status" in values:
            conversation.status = values["status"]
            conversation.archived_at = timezone.now() if values["status"] == Conversation.Status.ARCHIVED else None
        conversation.save()
        conversation.message_count = conversation.messages.count()
        conversation.latest_messages = list(conversation.messages.order_by("-sequence")[:1])
        return Response(ConversationSerializer(conversation).data)

    def delete(self, request, conversation_id):
        conversation = self.get_object(request.user, conversation_id)
        conversation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConversationMessageView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, conversation_id):
        conversation = get_object_or_404(
            owner_conversations(request.user),
            conversation_id=conversation_id,
            status=Conversation.Status.ACTIVE,
        )
        serializer = MessageInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        content = serializer.validated_data["content"]
        user_message = append_message(conversation, ConversationMessage.Role.USER, content)
        task = discover_agents(request.user, {"request_text": content})
        agent_message = append_message(
            conversation,
            ConversationMessage.Role.AGENT,
            task.agent_response,
            task=task,
        )
        if conversation.title == "New conversation":
            conversation.title = content[:72] + ("..." if len(content) > 72 else "")
            conversation.save(update_fields=["title", "updated_at"])
        task = Task.objects.prefetch_related("steps", "candidates__agent").get(pk=task.pk)
        payload = {
            "user_message": user_message,
            "agent_message": agent_message,
            "task": task,
        }
        return Response(ConversationSendSerializer(payload).data, status=status.HTTP_201_CREATED)
