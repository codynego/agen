from django.db import transaction
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.agents.services import provision_personal_agent

from .models import UserProfile
from .serializers import OnboardingSerializer, OnboardingStatusSerializer, onboarding_status


class OnboardingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        agent, _ = provision_personal_agent(request.user)
        return Response(OnboardingStatusSerializer(onboarding_status(request.user, profile, agent)).data)

    @transaction.atomic
    def post(self, request):
        serializer = OnboardingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        profile, _ = UserProfile.objects.select_for_update().get_or_create(user=request.user)
        agent, _ = provision_personal_agent(request.user)
        agent.name = data["agent_name"]
        agent.save(update_fields=["name", "updated_at"])

        profile.goal_categories = data["goals"]
        profile.integration_interests = data["integrations"]
        profile.approval_mode = data["approval_mode"]
        profile.decision_style = data["approval_mode"]
        profile.goals_summary = ", ".join(data["goals"])
        profile.onboarding_completed = True
        profile.onboarding_completed_at = timezone.now()
        profile.save()

        return Response(OnboardingStatusSerializer(onboarding_status(request.user, profile, agent)).data)
