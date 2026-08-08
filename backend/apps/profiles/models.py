from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=120, blank=True)
    budget_currency = models.CharField(max_length=8, default="NGN")
    decision_style = models.CharField(max_length=80, blank=True)
    goals_summary = models.TextField(blank=True)
    timezone = models.CharField(max_length=64, default="Africa/Lagos")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.display_name or self.user.get_username()

