from django.urls import path

from .views import (
    AgentDetailView,
    AgentListView,
    BusinessAgentView,
    DashboardView,
    PersonalAgentProvisionView,
    PublicAgentHandleView,
    PublicAgentVerificationView,
    PublicTrustHistoryView,
)
from .resolver_views import (
    ConnectionApprovalView,
    ConnectionRequestView,
    ConnectionResultView,
    ResolverDiscoveryView,
    ProviderConnectionListView,
    TaskDetailView,
    TaskListView,
)
from .conversation_views import ConversationDetailView, ConversationListCreateView, ConversationMessageView

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("conversations/", ConversationListCreateView.as_view(), name="conversation-list-create"),
    path("conversations/<uuid:conversation_id>/", ConversationDetailView.as_view(), name="conversation-detail"),
    path("conversations/<uuid:conversation_id>/messages/", ConversationMessageView.as_view(), name="conversation-message"),
    path("resolver/discover/", ResolverDiscoveryView.as_view(), name="resolver-discover"),
    path("resolver/tasks/", TaskListView.as_view(), name="resolver-task-list"),
    path("resolver/tasks/<uuid:task_id>/", TaskDetailView.as_view(), name="resolver-task-detail"),
    path("resolver/tasks/<uuid:task_id>/connect/", ConnectionRequestView.as_view(), name="resolver-connect"),
    path("resolver/connections/<uuid:connection_id>/approve/", ConnectionApprovalView.as_view(), name="resolver-approve"),
    path("resolver/connections/<uuid:connection_id>/result/", ConnectionResultView.as_view(), name="resolver-result"),
    path("resolver/provider/connections/", ProviderConnectionListView.as_view(), name="resolver-provider-connections"),
    path("agents/", AgentListView.as_view(), name="agent-list"),
    path("agents/personal/provision/", PersonalAgentProvisionView.as_view(), name="personal-agent-provision"),
    path("agents/business/", BusinessAgentView.as_view(), name="business-agent-list-create"),
    path("agents/handle/<slug:network_handle>/", PublicAgentHandleView.as_view(), name="agent-handle"),
    path("agents/verify/<uuid:agent_id>/", PublicAgentVerificationView.as_view(), name="agent-verification"),
    path("agents/verify/<uuid:agent_id>/trust/", PublicTrustHistoryView.as_view(), name="agent-trust-history"),
    path("agents/<slug:slug>/", AgentDetailView.as_view(), name="agent-detail"),
]
