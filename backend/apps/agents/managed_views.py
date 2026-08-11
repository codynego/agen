import json

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .conversation_crypto import encrypt_message
from .managed_agents import (
    INDUSTRY_TEMPLATES,
    apply_template,
    audit,
    development_verify,
    readiness,
    run_sandbox,
    submit_manual_verification,
    verify_business_domain,
)
from .managed_serializers import (
    CatalogItemSerializer,
    KnowledgeInputSerializer,
    KnowledgeSerializer,
    ManagedSettingsInputSerializer,
    ManagedSetupSerializer,
    SandboxInputSerializer,
    TestRunSerializer,
    ToolConnectionSerializer,
    ToolInputSerializer,
    VerificationInputSerializer,
)
from .models import Agent, AgentCatalogItem, AgentKnowledgeSource, AgentToolConnection, ManagedAgentProfile


def managed_agent(user, agent_id):
    return get_object_or_404(
        Agent.objects.filter(owner=user, kind=Agent.Kind.BUSINESS, hosting_type=Agent.HostingType.MANAGED),
        agent_id=agent_id,
    )


def setup_payload(agent):
    profile, _ = ManagedAgentProfile.objects.get_or_create(agent=agent)
    return {
        "agent": agent,
        "profile": profile,
        "knowledge": agent.knowledge_sources.all(),
        "catalog": agent.catalog_items.all(),
        "tools": agent.tool_connections.all(),
        "tests": agent.test_runs.all()[:10],
        "audit": agent.audit_events.all()[:20],
    }


class ManagedAgentSetupView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, agent_id):
        return Response(ManagedSetupSerializer(setup_payload(managed_agent(request.user, agent_id))).data)

    @transaction.atomic
    def patch(self, request, agent_id):
        agent = managed_agent(request.user, agent_id)
        serializer = ManagedSettingsInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile, _ = ManagedAgentProfile.objects.get_or_create(agent=agent)
        profile_fields = {"instructions", "tone", "human_handoff"}
        agent_fields = {"name", "company_name", "summary", "capabilities", "allowed_actions", "blocked_actions"}
        for field, value in serializer.validated_data.items():
            if field in profile_fields:
                setattr(profile, field, value)
            elif field in agent_fields:
                setattr(agent, field, value)
        profile.save()
        agent.save()
        audit(agent, request.user, "settings_updated", "Managed agent configuration updated")
        return Response(ManagedSetupSerializer(setup_payload(agent)).data)


class ManagedAgentTemplateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, agent_id, template_key):
        agent = managed_agent(request.user, agent_id)
        if template_key not in INDUSTRY_TEMPLATES:
            return Response({"detail": "Unknown industry template."}, status=status.HTTP_404_NOT_FOUND)
        apply_template(agent, request.user, template_key)
        return Response(ManagedSetupSerializer(setup_payload(agent)).data)


class ManagedAgentVerificationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, agent_id):
        agent = managed_agent(request.user, agent_id)
        serializer = VerificationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        method = values["method"]
        if method == "domain":
            try:
                verify_business_domain(agent, request.user, values["domain"])
            except ValueError as exc:
                return Response({"domain": [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)
        elif method == "manual":
            submit_manual_verification(agent, request.user, values)
        else:
            if not settings.DEBUG or not settings.BUSINESS_DEV_VERIFICATION_CODE:
                return Response({"detail": "Development verification is disabled."}, status=status.HTTP_404_NOT_FOUND)
            if values["development_code"] != settings.BUSINESS_DEV_VERIFICATION_CODE:
                return Response({"development_code": ["The local verification code is incorrect."]}, status=status.HTTP_400_BAD_REQUEST)
            development_verify(agent, request.user, values["requested_level"])
        return Response(ManagedSetupSerializer(setup_payload(agent)).data)


class ManagedAgentKnowledgeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, agent_id):
        agent = managed_agent(request.user, agent_id)
        serializer = KnowledgeInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        source = AgentKnowledgeSource.objects.create(
            agent=agent,
            kind=values["kind"],
            title=values["title"],
            content_ciphertext=encrypt_message(values["content"]),
            source_url=values.get("source_url", ""),
        )
        audit(agent, request.user, "knowledge_added", source.title, {"kind": source.kind})
        return Response(KnowledgeSerializer(source).data, status=status.HTTP_201_CREATED)


class ManagedAgentKnowledgeDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, agent_id, source_id):
        agent = managed_agent(request.user, agent_id)
        source = get_object_or_404(agent.knowledge_sources, source_id=source_id)
        title = source.title
        source.delete()
        audit(agent, request.user, "knowledge_deleted", title)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ManagedAgentCatalogView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, agent_id):
        agent = managed_agent(request.user, agent_id)
        serializer = CatalogItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = serializer.save(agent=agent)
        audit(agent, request.user, "catalog_item_added", item.name)
        return Response(CatalogItemSerializer(item).data, status=status.HTTP_201_CREATED)


class ManagedAgentCatalogDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, agent_id, item_id):
        agent = managed_agent(request.user, agent_id)
        item = get_object_or_404(agent.catalog_items, item_id=item_id)
        name = item.name
        item.delete()
        audit(agent, request.user, "catalog_item_deleted", name)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ManagedAgentToolView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, agent_id):
        agent = managed_agent(request.user, agent_id)
        serializer = ToolInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        config = values.pop("secret_config", {})
        tool, _ = AgentToolConnection.objects.update_or_create(
            agent=agent,
            provider=values.pop("provider"),
            defaults={
                **values,
                "config_ciphertext": encrypt_message(json.dumps(config)) if config else "",
                "status": AgentToolConnection.Status.CONNECTED,
                "last_tested_at": timezone.now(),
            },
        )
        audit(agent, request.user, "tool_connected", tool.display_name, {"provider": tool.provider})
        return Response(ToolConnectionSerializer(tool).data, status=status.HTTP_201_CREATED)


class ManagedAgentToolDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, agent_id, connection_id):
        agent = managed_agent(request.user, agent_id)
        tool = get_object_or_404(agent.tool_connections, connection_id=connection_id)
        name = tool.display_name
        tool.delete()
        audit(agent, request.user, "tool_disconnected", name)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ManagedAgentSandboxView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, agent_id):
        agent = managed_agent(request.user, agent_id)
        serializer = SandboxInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        run = run_sandbox(agent, serializer.validated_data["prompt"])
        audit(agent, request.user, "sandbox_tested", run.status, {"run_id": str(run.run_id)})
        return Response(TestRunSerializer(run).data, status=status.HTTP_201_CREATED)


class ManagedAgentActivationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, agent_id):
        agent = managed_agent(request.user, agent_id)
        state = readiness(agent)
        if not state["ready"]:
            missing = [key for key, complete in state["checks"].items() if not complete]
            return Response({"detail": "Complete every activation requirement first.", "missing": missing}, status=status.HTTP_400_BAD_REQUEST)
        agent.status = Agent.Status.ACTIVE
        agent.online = True
        agent.save(update_fields=["status", "online", "updated_at"])
        audit(agent, request.user, "agent_activated", "Agent is discoverable on the network")
        return Response(ManagedSetupSerializer(setup_payload(agent)).data)
