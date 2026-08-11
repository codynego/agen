import hashlib

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AgentActivity, AgentConnection, Task, TaskCandidate, TaskResult, TaskStep, TrustEvent
from .resolver import approve_connection, discover_agents, request_connection
from .resolver_serializers import (
    ConnectionApprovalSerializer,
    ConnectionRequestSerializer,
    ConnectionSerializer,
    DiscoveryRequestSerializer,
    TaskResultInputSerializer,
    TaskResultSerializer,
    TaskSerializer,
    ProviderConnectionSerializer,
)


def owner_tasks(user):
    return Task.objects.filter(owner=user).prefetch_related("steps", "candidates__agent")


class ResolverDiscoveryView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DiscoveryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = discover_agents(request.user, serializer.validated_data)
        task = owner_tasks(request.user).get(pk=task.pk)
        return Response(TaskSerializer(task).data, status=status.HTTP_201_CREATED)


class TaskListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TaskSerializer

    def get_queryset(self):
        return owner_tasks(self.request.user)


class TaskDetailView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TaskSerializer
    lookup_field = "task_id"
    lookup_url_kwarg = "task_id"

    def get_queryset(self):
        return owner_tasks(self.request.user)


class ConnectionRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        task = get_object_or_404(owner_tasks(request.user), task_id=task_id)
        serializer = ConnectionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        candidate = get_object_or_404(
            TaskCandidate.objects.select_related("agent"),
            task=task,
            agent__network_handle=serializer.validated_data["candidate_handle"],
        )
        if AgentConnection.objects.filter(task=task, provider_agent=candidate.agent).exists():
            return Response({"detail": "A connection to this agent already exists for the task."}, status=status.HTTP_409_CONFLICT)
        connection = request_connection(request.user, task, candidate, serializer.validated_data["scopes"])
        connection = AgentConnection.objects.select_related("task", "provider_agent").get(pk=connection.pk)
        return Response(ConnectionSerializer(connection).data, status=status.HTTP_201_CREATED)


class ConnectionApprovalView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, connection_id):
        connection = get_object_or_404(
            AgentConnection.objects.select_related("task", "provider_agent"),
            connection_id=connection_id,
            task__owner=request.user,
        )
        serializer = ConnectionApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scopes = serializer.validated_data["scopes"] or connection.requested_scopes
        if not set(scopes).issubset(connection.requested_scopes):
            return Response({"scopes": ["Approval cannot add permissions that were not requested."]}, status=status.HTTP_400_BAD_REQUEST)
        connection = approve_connection(connection, scopes)
        return Response(ConnectionSerializer(connection).data)


class ProviderConnectionListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProviderConnectionSerializer

    def get_queryset(self):
        return AgentConnection.objects.filter(
            provider_agent__owner=self.request.user,
            status__in=[AgentConnection.Status.APPROVED, AgentConnection.Status.ACTIVE],
        ).select_related("task", "requester_agent", "data_grant")


class ConnectionResultView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, connection_id):
        connection = get_object_or_404(
            AgentConnection.objects.select_related("task", "provider_agent"),
            connection_id=connection_id,
            provider_agent__owner=request.user,
            status__in=[AgentConnection.Status.APPROVED, AgentConnection.Status.ACTIVE],
        )
        serializer = TaskResultInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result, created = TaskResult.objects.get_or_create(
            task=connection.task,
            defaults={"connection": connection, **serializer.validated_data, "delivered_at": timezone.now()},
        )
        if not created:
            return Response({"detail": "A result has already been submitted for this task."}, status=status.HTTP_409_CONFLICT)
        connection.status = AgentConnection.Status.COMPLETED
        connection.save(update_fields=["status", "updated_at"])
        connection.task.status = Task.Status.COMPLETED
        connection.task.save(update_fields=["status", "updated_at"])
        connection.task.steps.filter(position=3).update(status=TaskStep.Status.COMPLETED)
        evidence_hash = serializer.validated_data.get("evidence_hash") or hashlib.sha256(
            serializer.validated_data["summary"].encode("utf-8")
        ).hexdigest()
        TrustEvent.objects.create(
            subject_agent=connection.provider_agent,
            source_agent=connection.requester_agent,
            category=TrustEvent.Category.TASK_COMPLETED,
            outcome=TrustEvent.Outcome.POSITIVE,
            score_delta="2.0",
            evidence_hash=evidence_hash,
            metadata={"task_id": str(connection.task.task_id), "result_id": str(result.result_id)},
        )
        AgentActivity.objects.create(
            agent=connection.provider_agent,
            title="Network task completed",
            detail=f"Delivered result for task {connection.task.task_id}",
        )
        if connection.provider_agent.hosting_type == connection.provider_agent.HostingType.MANAGED:
            from .managed_agents import audit

            audit(
                connection.provider_agent,
                request.user,
                "network_task_completed",
                serializer.validated_data["summary"][:240],
                {"task_id": str(connection.task.task_id), "evidence_hash": evidence_hash},
            )
        if hasattr(connection.task, "conversation_message"):
            from .conversation_services import append_message
            from .models import ConversationMessage

            append_message(
                connection.task.conversation_message.conversation,
                ConversationMessage.Role.AGENT,
                serializer.validated_data["summary"],
            )
        return Response(TaskResultSerializer(result).data, status=status.HTTP_201_CREATED)
