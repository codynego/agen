from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
import re

from django.db import transaction
from django.utils import timezone

from apps.profiles.models import UserProfile

from .models import Agent, AgentConnection, DataGrant, Task, TaskCandidate, TaskStep
from .services import provision_personal_agent


CAPABILITY_RULES = {
    "restaurant_search": ("restaurant", "dinner", "lunch", "table"),
    "reservation": ("reserve", "reservation", "book a table"),
    "travel_search": ("flight", "hotel", "trip", "travel"),
    "booking": ("book", "booking", "reserve"),
    "telecom_compare": ("data plan", "mobile plan", "internet plan", "network plan"),
    "product_search": ("laptop", "phone", "shopping", "buy", "purchase"),
    "price_compare": ("compare", "deal", "cheaper", "price"),
    "research": ("research", "find", "investigate", "explain"),
}

SENSITIVE_SCOPES = {"contact_details", "files_read", "email_send", "payment"}
ALLOWED_SCOPES = {"task_context", "location", "schedule", "budget_limit", *SENSITIVE_SCOPES}

EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
LONG_NUMBER_PATTERN = re.compile(r"(?<!\w)\+?[\d][\d\s()-]{7,}[\d](?!\w)")


def infer_capabilities(request_text: str) -> list[str]:
    normalized = request_text.lower()
    inferred = [capability for capability, terms in CAPABILITY_RULES.items() if any(term in normalized for term in terms)]
    return inferred or ["general_assistance"]


def infer_risk(request_text: str, scopes: list[str] | None = None) -> str:
    normalized = request_text.lower()
    requested_scopes = set(scopes or [])
    if requested_scopes & SENSITIVE_SCOPES or any(term in normalized for term in ("pay", "purchase", "send money", "password")):
        return Task.RiskLevel.HIGH
    if any(term in normalized for term in ("email", "message", "upload", "personal")):
        return Task.RiskLevel.MEDIUM
    return Task.RiskLevel.LOW


def sanitize_task_brief(request_text: str) -> str:
    brief = EMAIL_PATTERN.sub("[email redacted]", request_text.strip())
    return LONG_NUMBER_PATTERN.sub("[number redacted]", brief)


def build_discovery_spec(data: dict) -> dict:
    capabilities = list(dict.fromkeys(data.get("capabilities") or infer_capabilities(data["request_text"])))
    spec = {"capabilities": capabilities, "brief": sanitize_task_brief(data["request_text"])}
    if data.get("location"):
        spec["location"] = data["location"].strip()
    if data.get("max_budget") is not None:
        spec["budget"] = {"maximum": str(data["max_budget"]), "currency": data.get("currency", "NGN")}
    return spec


def candidate_score(agent: Agent, spec: dict) -> tuple[Decimal, list[str]] | None:
    required = set(spec["capabilities"])
    offered = set(agent.capabilities)
    matched = required & offered
    if not matched:
        return None

    coverage = Decimal(len(matched)) / Decimal(len(required))
    score = coverage * Decimal("60") + Decimal(agent.trust_score) * Decimal("0.30") + Decimal("5")
    reasons = [f"Matches {len(matched)} of {len(required)} required capabilities", "Identity verified", "Currently available"]
    location = spec.get("location", "").lower()
    if location and agent.location and location in agent.location.lower():
        score += Decimal("5")
        reasons.append("Location matched")
    return min(score, Decimal("100")), reasons


@transaction.atomic
def discover_agents(user, data: dict) -> Task:
    personal_agent, _ = provision_personal_agent(user)
    spec = build_discovery_spec(data)
    task = Task.objects.create(
        owner=user,
        personal_agent=personal_agent,
        request_text=data["request_text"],
        discovery_spec=spec,
        risk_level=infer_risk(data["request_text"]),
    )
    TaskStep.objects.bulk_create([
        TaskStep(task=task, position=1, title="Understand request", status=TaskStep.Status.COMPLETED),
        TaskStep(task=task, position=2, title="Resolve compatible agents", status=TaskStep.Status.ACTIVE),
        TaskStep(task=task, position=3, title="Connect and complete task"),
    ])

    ranked = []
    queryset = Agent.objects.filter(
        kind=Agent.Kind.BUSINESS,
        status=Agent.Status.ACTIVE,
        verified=True,
        online=True,
    )
    for agent in queryset:
        scored = candidate_score(agent, spec)
        if scored:
            ranked.append((agent, *scored))
    ranked.sort(key=lambda item: (item[1], item[0].trust_score), reverse=True)

    TaskCandidate.objects.bulk_create([
        TaskCandidate(
            task=task,
            agent=agent,
            rank=rank,
            match_score=score,
            trust_score_snapshot=agent.trust_score,
            reasons=reasons,
        )
        for rank, (agent, score, reasons) in enumerate(ranked[:10], start=1)
    ])
    task.steps.filter(position=2).update(status=TaskStep.Status.COMPLETED)
    if ranked:
        task.status = Task.Status.AWAITING_APPROVAL
        task.save(update_fields=["status", "updated_at"])
    return task


def connection_can_auto_approve(profile: UserProfile, task: Task, provider: Agent, scopes: list[str]) -> bool:
    return (
        profile.approval_mode == UserProfile.ApprovalMode.AUTO_CONNECT
        and task.risk_level == Task.RiskLevel.LOW
        and provider.trust_level == Agent.TrustLevel.HIGH_TRUST
        and not set(scopes) & SENSITIVE_SCOPES
    )


def issue_data_grant(connection: AgentConnection, scopes: list[str]) -> DataGrant:
    return DataGrant.objects.create(
        connection=connection,
        scopes=scopes,
        expires_at=timezone.now() + timedelta(minutes=30),
    )


@transaction.atomic
def request_connection(user, task: Task, candidate: TaskCandidate, scopes: list[str]) -> AgentConnection:
    profile, _ = UserProfile.objects.get_or_create(user=user)
    auto_approved = connection_can_auto_approve(profile, task, candidate.agent, scopes)
    status = AgentConnection.Status.APPROVED if auto_approved else AgentConnection.Status.PENDING_APPROVAL
    connection = AgentConnection.objects.create(
        task=task,
        requester_agent=task.personal_agent,
        provider_agent=candidate.agent,
        status=status,
        auto_approved=auto_approved,
        requested_scopes=scopes,
        trust_score_snapshot=candidate.agent.trust_score,
        approved_at=timezone.now() if auto_approved else None,
    )
    if auto_approved:
        issue_data_grant(connection, scopes)
        task.status = Task.Status.CONNECTING
    else:
        task.status = Task.Status.AWAITING_APPROVAL
    task.save(update_fields=["status", "updated_at"])
    return connection


@transaction.atomic
def approve_connection(connection: AgentConnection, scopes: list[str]) -> AgentConnection:
    if connection.status != AgentConnection.Status.PENDING_APPROVAL:
        return connection
    connection.status = AgentConnection.Status.APPROVED
    connection.approved_at = timezone.now()
    connection.save(update_fields=["status", "approved_at", "updated_at"])
    issue_data_grant(connection, scopes)
    connection.task.status = Task.Status.CONNECTING
    connection.task.save(update_fields=["status", "updated_at"])
    return connection
