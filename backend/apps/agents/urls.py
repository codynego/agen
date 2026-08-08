from django.urls import path

from .views import (
    AgentDetailView,
    AgentListView,
    BusinessAgentView,
    DashboardView,
    PersonalAgentProvisionView,
    PublicAgentVerificationView,
    PublicTrustHistoryView,
)

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("agents/", AgentListView.as_view(), name="agent-list"),
    path("agents/personal/provision/", PersonalAgentProvisionView.as_view(), name="personal-agent-provision"),
    path("agents/business/", BusinessAgentView.as_view(), name="business-agent-list-create"),
    path("agents/verify/<uuid:agent_id>/", PublicAgentVerificationView.as_view(), name="agent-verification"),
    path("agents/verify/<uuid:agent_id>/trust/", PublicTrustHistoryView.as_view(), name="agent-trust-history"),
    path("agents/<slug:slug>/", AgentDetailView.as_view(), name="agent-detail"),
]
