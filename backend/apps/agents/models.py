from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.text import slugify


class Agent(models.Model):
    class Kind(models.TextChoices):
        PERSONAL = "personal", "Personal"
        BUSINESS = "business", "Business"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"

    class TrustLevel(models.TextChoices):
        UNVERIFIED = "unverified", "Unverified"
        DEVELOPING = "developing", "Developing"
        TRUSTED = "trusted", "Trusted"
        HIGH_TRUST = "high_trust", "High trust"

    class HostingType(models.TextChoices):
        MANAGED = "managed", "Managed by Agen"
        EXTERNAL = "external", "External endpoint"

    agent_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="agents")
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True, max_length=140)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.BUSINESS)
    hosting_type = models.CharField(max_length=20, choices=HostingType.choices, default=HostingType.MANAGED)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    category = models.CharField(max_length=80)
    company_name = models.CharField(max_length=120, blank=True)
    location = models.CharField(max_length=120, blank=True)
    endpoint = models.CharField(max_length=255, blank=True)
    summary = models.TextField(blank=True)
    trust_score = models.DecimalField(max_digits=4, decimal_places=1, default=40.0, editable=False)
    trust_level = models.CharField(
        max_length=20,
        choices=TrustLevel.choices,
        default=TrustLevel.UNVERIFIED,
        editable=False,
    )
    verified = models.BooleanField(default=False)
    identity_key_fingerprint = models.CharField(max_length=64, blank=True, editable=False)
    identity_verified_at = models.DateTimeField(null=True, blank=True, editable=False)
    online = models.BooleanField(default=True)
    capabilities = models.JSONField(default=list, blank=True)
    allowed_actions = models.JSONField(default=list, blank=True)
    blocked_actions = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-verified", "-trust_score", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner"],
                condition=Q(kind="personal"),
                name="one_personal_agent_per_owner",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class AgentActivity(models.Model):
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="activities")
    title = models.CharField(max_length=140)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class TrustEvent(models.Model):
    class Category(models.TextChoices):
        IDENTITY_VERIFIED = "identity_verified", "Identity verified"
        TASK_COMPLETED = "task_completed", "Task completed"
        PEER_ATTESTATION = "peer_attestation", "Peer attestation"
        DISPUTE_RESOLVED = "dispute_resolved", "Dispute resolved"
        POLICY_VIOLATION = "policy_violation", "Policy violation"

    class Outcome(models.TextChoices):
        POSITIVE = "positive", "Positive"
        NEUTRAL = "neutral", "Neutral"
        NEGATIVE = "negative", "Negative"

    event_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    subject_agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="trust_events")
    source_agent = models.ForeignKey(
        Agent,
        on_delete=models.SET_NULL,
        related_name="issued_trust_events",
        null=True,
        blank=True,
    )
    category = models.CharField(max_length=30, choices=Category.choices)
    outcome = models.CharField(max_length=10, choices=Outcome.choices)
    score_delta = models.DecimalField(max_digits=4, decimal_places=1)
    evidence_hash = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(score_delta__gte=-20) & Q(score_delta__lte=10),
                name="trust_event_delta_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.subject_agent.name}: {self.category}"
