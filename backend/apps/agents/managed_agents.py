from __future__ import annotations

import re

from django.db import transaction
from django.utils import timezone

from .conversation_crypto import decrypt_message, encrypt_message
from .models import (
    Agent,
    AgentAuditEvent,
    AgentKnowledgeSource,
    AgentTestRun,
    ManagedAgentProfile,
    TrustEvent,
)


INDUSTRY_TEMPLATES = {
    "commerce": {
        "name": "Commerce",
        "description": "Product discovery, availability, orders, delivery, and returns.",
        "capabilities": ["product_search", "price_quote", "order_status", "returns_support"],
        "instructions": "Help customers find suitable products. Confirm price, availability, delivery terms, and approval before any purchase or refund action.",
        "starter_knowledge": [("Ordering and returns", "Explain ordering, delivery, return windows, and refund conditions using only the business's supplied policies.")],
    },
    "customer_support": {
        "name": "Customer support",
        "description": "FAQs, troubleshooting, ticket intake, and human escalation.",
        "capabilities": ["customer_support", "faq_answering", "ticket_intake", "human_handoff"],
        "instructions": "Answer from verified business knowledge, gather only necessary details, and escalate when the answer is uncertain or the customer requests a person.",
        "starter_knowledge": [("Support escalation", "Escalate unresolved, sensitive, or account-specific requests to an authorized human support channel.")],
    },
    "hospitality": {
        "name": "Travel and hospitality",
        "description": "Availability, reservations, guest information, and service policies.",
        "capabilities": ["availability_search", "reservation", "guest_support", "policy_answering"],
        "instructions": "Confirm dates, party size, price, cancellation terms, and approval before creating or changing a reservation.",
        "starter_knowledge": [("Reservation policy", "Use the business's current availability, pricing, cancellation, and guest policies for every reservation request.")],
    },
    "professional_services": {
        "name": "Professional services",
        "description": "Service discovery, qualification, scheduling, and client intake.",
        "capabilities": ["service_discovery", "client_intake", "scheduling", "proposal_support"],
        "instructions": "Qualify the request, explain services without inventing guarantees, and obtain approval before scheduling or sending information externally.",
        "starter_knowledge": [("Client intake", "Collect the objective, timeline, location, and constraints needed to route a client request.")],
    },
}

VERIFICATION_LEVEL_ORDER = {
    ManagedAgentProfile.VerificationLevel.NONE: 0,
    ManagedAgentProfile.VerificationLevel.BASIC: 1,
    ManagedAgentProfile.VerificationLevel.BUSINESS: 2,
    ManagedAgentProfile.VerificationLevel.ENHANCED: 3,
}
SENSITIVE_VERIFICATION_TERMS = {"payment", "refund", "financial", "health", "medical", "credit", "debit"}
TRANSACTIONAL_VERIFICATION_TERMS = {"book", "booking", "reservation", "order", "purchase", "schedule", "send", "update", "create"}


def audit(agent: Agent, actor, action: str, detail: str = "", metadata: dict | None = None):
    return AgentAuditEvent.objects.create(
        agent=agent,
        actor=actor,
        action=action,
        detail=detail[:240],
        metadata=metadata or {},
    )


@transaction.atomic
def apply_template(agent: Agent, actor, template_key: str) -> ManagedAgentProfile:
    template = INDUSTRY_TEMPLATES[template_key]
    profile, _ = ManagedAgentProfile.objects.select_for_update().get_or_create(agent=agent)
    profile.template_key = template_key
    if not profile.instructions:
        profile.instructions = template["instructions"]
    profile.save()
    agent.capabilities = list(dict.fromkeys([*agent.capabilities, *template["capabilities"]]))
    agent.save(update_fields=["capabilities", "updated_at"])
    for title, content in template["starter_knowledge"]:
        AgentKnowledgeSource.objects.get_or_create(
            agent=agent,
            title=title,
            defaults={"kind": AgentKnowledgeSource.Kind.NOTE, "content_ciphertext": encrypt_message(content)},
        )
    audit(agent, actor, "template_applied", template["name"])
    return profile


def readiness(agent: Agent) -> dict:
    profile, _ = ManagedAgentProfile.objects.get_or_create(agent=agent)
    required_level = required_verification_level(agent)
    checks = {
        "business_verified": (
            profile.verification_status == ManagedAgentProfile.VerificationStatus.VERIFIED
            and VERIFICATION_LEVEL_ORDER[profile.verification_level] >= VERIFICATION_LEVEL_ORDER[required_level]
        ),
        "template_selected": bool(profile.template_key),
        "knowledge_added": agent.knowledge_sources.filter(active=True).exists(),
        "instructions_configured": bool(profile.instructions.strip()),
        "capabilities_configured": bool(agent.capabilities),
        "sandbox_test_passed": agent.test_runs.filter(status=AgentTestRun.Status.PASSED).exists(),
    }
    return {
        "ready": all(checks.values()),
        "checks": checks,
        "required_verification_level": required_level,
        "current_verification_level": profile.verification_level,
    }


def required_verification_level(agent: Agent) -> str:
    terms = " ".join([*agent.capabilities, *agent.allowed_actions]).lower()
    if any(term in terms for term in SENSITIVE_VERIFICATION_TERMS):
        return ManagedAgentProfile.VerificationLevel.ENHANCED
    if agent.tool_connections.exists() or any(term in terms for term in TRANSACTIONAL_VERIFICATION_TERMS):
        return ManagedAgentProfile.VerificationLevel.BUSINESS
    return ManagedAgentProfile.VerificationLevel.BASIC


def complete_verification(agent: Agent, actor, profile: ManagedAgentProfile, level: str, method: str):
    profile.verification_status = ManagedAgentProfile.VerificationStatus.VERIFIED
    profile.verification_level = level
    profile.verification_method = method
    profile.save()
    if not agent.verified:
        agent.verified = True
        agent.identity_verified_at = timezone.now()
        agent.save(update_fields=["verified", "identity_verified_at", "updated_at"])
        TrustEvent.objects.create(
            subject_agent=agent,
            category=TrustEvent.Category.IDENTITY_VERIFIED,
            outcome=TrustEvent.Outcome.POSITIVE,
            score_delta="5.0",
            metadata={"method": method, "level": level},
        )
    audit(agent, actor, "business_verified", f"{level.title()} verification", {"method": method})


def verify_business_domain(agent: Agent, actor, domain: str) -> ManagedAgentProfile:
    normalized = domain.lower().strip().removeprefix("https://").removeprefix("http://").split("/")[0]
    if not re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", normalized):
        raise ValueError("Enter a valid business domain.")
    profile, _ = ManagedAgentProfile.objects.get_or_create(agent=agent)
    profile.business_domain = normalized
    profile.verification_submitted_at = timezone.now()
    profile.requested_verification_level = ManagedAgentProfile.VerificationLevel.BUSINESS
    profile.verification_method = ManagedAgentProfile.VerificationMethod.DOMAIN_EMAIL
    email_domain = (actor.email or "").lower().partition("@")[2]
    verified = email_domain == normalized or email_domain.endswith(f".{normalized}")
    if verified:
        complete_verification(
            agent,
            actor,
            profile,
            ManagedAgentProfile.VerificationLevel.BUSINESS,
            ManagedAgentProfile.VerificationMethod.DOMAIN_EMAIL,
        )
    else:
        profile.verification_status = ManagedAgentProfile.VerificationStatus.PENDING
        profile.save()
    audit(agent, actor, "verification_submitted", f"Domain: {normalized}", {"auto_verified": verified})
    return profile


def submit_manual_verification(agent: Agent, actor, data: dict) -> ManagedAgentProfile:
    profile, _ = ManagedAgentProfile.objects.get_or_create(agent=agent)
    profile.verification_status = ManagedAgentProfile.VerificationStatus.PENDING
    profile.verification_method = ManagedAgentProfile.VerificationMethod.MANUAL_REVIEW
    profile.requested_verification_level = data["requested_level"]
    profile.country = data["country"]
    profile.registration_number = data.get("registration_number", "")
    profile.business_phone = data["business_phone"]
    profile.supporting_url = data.get("supporting_url", "")
    profile.evidence_notes = data.get("evidence_notes", "")
    profile.verification_submitted_at = timezone.now()
    profile.save()
    audit(
        agent,
        actor,
        "manual_verification_submitted",
        f"{data['country']} · {data['requested_level']}",
        {"has_registration": bool(profile.registration_number), "has_supporting_url": bool(profile.supporting_url)},
    )
    return profile


def development_verify(agent: Agent, actor, requested_level: str) -> ManagedAgentProfile:
    profile, _ = ManagedAgentProfile.objects.get_or_create(agent=agent)
    profile.requested_verification_level = requested_level
    profile.verification_submitted_at = timezone.now()
    complete_verification(
        agent,
        actor,
        profile,
        requested_level,
        ManagedAgentProfile.VerificationMethod.DEVELOPMENT,
    )
    return profile


def run_sandbox(agent: Agent, prompt: str) -> AgentTestRun:
    words = {word for word in re.findall(r"[a-z0-9]+", prompt.lower()) if len(word) > 2}
    matches = []
    for source in agent.knowledge_sources.filter(active=True):
        content = decrypt_message(source.content_ciphertext)
        score = len(words & set(re.findall(r"[a-z0-9]+", f"{source.title} {content}".lower())))
        if score:
            matches.append((score, source.title, content))
    for item in agent.catalog_items.filter(active=True):
        score = len(words & set(re.findall(r"[a-z0-9]+", f"{item.name} {item.description} {item.sku}".lower())))
        if score:
            price = f" {item.currency} {item.price}" if item.price is not None else ""
            matches.append((score, item.name, f"{item.description}{price}. Availability: {item.availability}."))
    matches.sort(reverse=True, key=lambda item: item[0])
    if matches:
        context = "\n".join(f"- **{title}:** {content}" for _, title, content in matches[:3])
        response = f"## Based on {agent.company_name or agent.name}'s information\n\n{context}\n\nI would use this verified business context to handle the request. Any external action still requires its configured tool and approval policy."
        status = AgentTestRun.Status.PASSED
    else:
        response = "## More knowledge needed\n\nI could not find business information relevant to this request. Add an FAQ, policy, service, or catalogue item, then test again."
        status = AgentTestRun.Status.NEEDS_CONFIGURATION
    return AgentTestRun.objects.create(
        agent=agent,
        prompt=prompt,
        response=response,
        status=status,
        matched_sources=[title for _, title, _ in matches[:3]],
    )
