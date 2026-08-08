from __future__ import annotations

from decimal import Decimal
import uuid

from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce

from .models import Agent, AgentActivity, TrustEvent


def provision_personal_agent(user, name: str = "") -> tuple[Agent, bool]:
    display_name = user.get_full_name().strip() or user.get_username()
    agent_name = name.strip() or f"{display_name}'s Agen"
    return Agent.objects.get_or_create(
        owner=user,
        kind=Agent.Kind.PERSONAL,
        defaults={
            "name": agent_name,
            "slug": f"personal-{user.pk}",
            "status": Agent.Status.ACTIVE,
            "category": "Personal assistant",
            "summary": "A private personal agent that plans requests and coordinates trusted services.",
            "capabilities": ["plan", "research", "connect", "coordinate", "report"],
            "allowed_actions": ["discover_agents", "request_connection", "execute_approved_tasks"],
            "blocked_actions": ["share_private_data_without_permission", "approve_payments"],
        },
    )


def register_business_agent(user, data: dict) -> Agent:
    suffix = uuid.uuid4().hex[:8]
    return Agent.objects.create(
        owner=user,
        name=data["name"],
        slug=f"business-{user.pk}-{suffix}",
        kind=Agent.Kind.BUSINESS,
        hosting_type=data["hosting_type"],
        status=Agent.Status.DRAFT,
        company_name=data["company_name"],
        category=data["category"],
        summary=data.get("summary", ""),
        endpoint=data.get("endpoint", ""),
        capabilities=data.get("capabilities", []),
        allowed_actions=[],
        blocked_actions=["operate_before_verification", "request_unapproved_private_data"],
        online=False,
    )


def recalculate_trust_score(agent: Agent) -> Agent:
    event_total = agent.trust_events.aggregate(
        total=Coalesce(Sum("score_delta"), Decimal("0.0")),
    )["total"]
    identity_bonus = Decimal("20.0") if agent.identity_verified_at else Decimal("0.0")
    score = max(Decimal("0.0"), min(Decimal("100.0"), Decimal("40.0") + identity_bonus + event_total))

    if score >= 85:
        trust_level = Agent.TrustLevel.HIGH_TRUST
    elif score >= 70:
        trust_level = Agent.TrustLevel.TRUSTED
    elif score >= 50:
        trust_level = Agent.TrustLevel.DEVELOPING
    else:
        trust_level = Agent.TrustLevel.UNVERIFIED

    Agent.objects.filter(pk=agent.pk).update(trust_score=score, trust_level=trust_level)
    agent.trust_score = score
    agent.trust_level = trust_level
    return agent


def apply_agent_filters(queryset, params):
    query = params.get("query")
    category = params.get("category")
    location = params.get("location")
    capability = params.get("capability")
    trust_score = params.get("trust_score")
    verified_only = params.get("verified_only")
    online_only = params.get("online_only")

    if query:
        queryset = queryset.filter(
            Q(name__icontains=query)
            | Q(company_name__icontains=query)
            | Q(category__icontains=query)
            | Q(summary__icontains=query)
            | Q(capabilities__icontains=query)
        )
    if category:
        queryset = queryset.filter(category__icontains=category)
    if location:
        queryset = queryset.filter(location__icontains=location)
    if capability:
        queryset = queryset.filter(capabilities__icontains=capability)
    if trust_score:
        queryset = queryset.filter(trust_score__gte=trust_score)
    if verified_only in {"1", "true", "True"}:
        queryset = queryset.filter(verified=True)
    if online_only in {"1", "true", "True"}:
        queryset = queryset.filter(online=True)

    return queryset


def build_dashboard_snapshot() -> dict:
    agents = Agent.objects.all()
    personal_agent = agents.filter(kind=Agent.Kind.PERSONAL, status=Agent.Status.ACTIVE).first() or agents.filter(kind=Agent.Kind.PERSONAL).first()
    featured_agents = agents.filter(kind=Agent.Kind.BUSINESS, verified=True)[:4]
    recent_activity = list(
        AgentActivity.objects.select_related("agent")
        .order_by("-created_at")[:5]
        .values("title", "detail", "created_at", "agent__name", "agent__slug")
    )

    return {
        "greeting": "Good afternoon, Abednego",
        "metrics": {
            "my_agents": agents.filter(kind=Agent.Kind.PERSONAL).count(),
            "connected_agents": agents.filter(kind=Agent.Kind.BUSINESS).count(),
            "network_requests": AgentActivity.objects.count() * 14 + 2841 if agents.exists() else 2841,
            "successful_transactions": AgentActivity.objects.aggregate(total=Count("id"))["total"] * 8 + 1204 if AgentActivity.objects.exists() else 1204,
        },
        "personal_agent": personal_agent,
        "featured_agents": featured_agents,
        "recent_activity": recent_activity,
    }
