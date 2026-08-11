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
    network_handle = models.SlugField(unique=True, max_length=140, editable=False, db_index=True)
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
        if self._state.adding:
            prefix = "agen" if self.kind == self.Kind.PERSONAL else "agent"
            suffix = self.agent_id.hex[:12]
            candidate = f"{prefix}-{suffix}"
            while Agent.objects.filter(network_handle=candidate).exists():
                candidate = f"{prefix}-{uuid.uuid4().hex[:12]}"
            self.network_handle = candidate
        elif self.pk:
            stored_handle = Agent.objects.filter(pk=self.pk).values_list("network_handle", flat=True).first()
            if stored_handle:
                self.network_handle = stored_handle
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


class Task(models.Model):
    class Status(models.TextChoices):
        DISCOVERING = "discovering", "Discovering"
        AWAITING_APPROVAL = "awaiting_approval", "Awaiting approval"
        CONNECTING = "connecting", "Connecting"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    class RiskLevel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    task_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="agent_tasks")
    personal_agent = models.ForeignKey(Agent, on_delete=models.PROTECT, related_name="owned_tasks")
    request_text = models.TextField()
    discovery_spec = models.JSONField(default=dict)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DISCOVERING)
    risk_level = models.CharField(max_length=12, choices=RiskLevel.choices, default=RiskLevel.LOW)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.task_id}: {self.status}"


class TaskStep(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="steps")
    position = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=160)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position"]
        constraints = [models.UniqueConstraint(fields=["task", "position"], name="unique_task_step_position")]


class TaskCandidate(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="candidates")
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="task_candidates")
    rank = models.PositiveSmallIntegerField()
    match_score = models.DecimalField(max_digits=5, decimal_places=2)
    trust_score_snapshot = models.DecimalField(max_digits=4, decimal_places=1)
    reasons = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["rank"]
        constraints = [
            models.UniqueConstraint(fields=["task", "agent"], name="unique_agent_candidate_per_task"),
            models.UniqueConstraint(fields=["task", "rank"], name="unique_candidate_rank_per_task"),
        ]


class AgentConnection(models.Model):
    class Status(models.TextChoices):
        PENDING_APPROVAL = "pending_approval", "Pending approval"
        APPROVED = "approved", "Approved"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        REJECTED = "rejected", "Rejected"
        REVOKED = "revoked", "Revoked"

    connection_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="connections")
    requester_agent = models.ForeignKey(Agent, on_delete=models.PROTECT, related_name="outgoing_connections")
    provider_agent = models.ForeignKey(Agent, on_delete=models.PROTECT, related_name="incoming_connections")
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDING_APPROVAL)
    auto_approved = models.BooleanField(default=False)
    requested_scopes = models.JSONField(default=list)
    trust_score_snapshot = models.DecimalField(max_digits=4, decimal_places=1)
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["task", "provider_agent"], name="unique_provider_connection_per_task"),
            models.CheckConstraint(
                condition=~Q(requester_agent=models.F("provider_agent")),
                name="connection_agents_must_differ",
            ),
        ]


class DataGrant(models.Model):
    grant_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    connection = models.OneToOneField(AgentConnection, on_delete=models.CASCADE, related_name="data_grant")
    scopes = models.JSONField(default=list)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def active(self) -> bool:
        from django.utils import timezone

        return self.revoked_at is None and self.expires_at > timezone.now()


class TaskResult(models.Model):
    result_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    task = models.OneToOneField(Task, on_delete=models.CASCADE, related_name="result")
    connection = models.ForeignKey(AgentConnection, on_delete=models.SET_NULL, related_name="results", null=True, blank=True)
    summary = models.TextField()
    structured_result = models.JSONField(default=dict)
    evidence_hash = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
