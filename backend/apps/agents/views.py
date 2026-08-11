from __future__ import annotations

from django.db.models import Count
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Agent, TrustEvent
from .serializers import (
    AgentSerializer,
    BusinessAgentRegistrationSerializer,
    DashboardSerializer,
    PersonalAgentProvisionSerializer,
    PublicAgentVerificationSerializer,
    PublicTrustEventSerializer,
)
from .services import apply_agent_filters, build_dashboard_snapshot, provision_personal_agent, register_business_agent


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        snapshot = build_dashboard_snapshot(request.user)
        serializer = DashboardSerializer(snapshot)
        return Response(serializer.data)


class AgentListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AgentSerializer

    def get_queryset(self):
        queryset = Agent.objects.filter(owner=self.request.user).prefetch_related("activities")
        return apply_agent_filters(queryset, self.request.query_params)


class AgentDetailView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AgentSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return Agent.objects.filter(owner=self.request.user).prefetch_related("activities")


class PersonalAgentProvisionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PersonalAgentProvisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        agent, created = provision_personal_agent(request.user, serializer.validated_data.get("name", ""))
        response_serializer = AgentSerializer(agent, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class BusinessAgentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        agents = Agent.objects.filter(owner=request.user, kind=Agent.Kind.BUSINESS)
        return Response(AgentSerializer(agents, many=True, context={"request": request}).data)

    def post(self, request):
        serializer = BusinessAgentRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        agent = register_business_agent(request.user, serializer.validated_data)
        return Response(
            AgentSerializer(agent, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class PublicAgentVerificationView(RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = PublicAgentVerificationSerializer
    lookup_field = "agent_id"
    lookup_url_kwarg = "agent_id"

    def get_queryset(self):
        return Agent.objects.filter(status=Agent.Status.ACTIVE).annotate(trust_event_count=Count("trust_events"))


class PublicAgentHandleView(PublicAgentVerificationView):
    lookup_field = "network_handle"
    lookup_url_kwarg = "network_handle"


class PublicTrustHistoryView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = PublicTrustEventSerializer

    def get_queryset(self):
        return TrustEvent.objects.filter(
            subject_agent__agent_id=self.kwargs["agent_id"],
            subject_agent__status=Agent.Status.ACTIVE,
        ).select_related("source_agent")
