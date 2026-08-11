from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    class ApprovalMode(models.TextChoices):
        ALWAYS_ASK = "always_ask", "Always ask"
        BALANCED = "balanced", "Balanced"
        AUTO_CONNECT = "auto_connect", "Auto-connect"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=120, blank=True)
    budget_currency = models.CharField(max_length=8, default="NGN")
    decision_style = models.CharField(max_length=80, blank=True)
    goals_summary = models.TextField(blank=True)
    goal_categories = models.JSONField(default=list, blank=True)
    integration_interests = models.JSONField(default=list, blank=True)
    approval_mode = models.CharField(max_length=24, choices=ApprovalMode.choices, default=ApprovalMode.BALANCED)
    onboarding_completed = models.BooleanField(default=False)
    onboarding_completed_at = models.DateTimeField(null=True, blank=True)
    timezone = models.CharField(max_length=64, default="Africa/Lagos")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.display_name or self.user.get_username()
