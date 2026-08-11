from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "approval_mode", "onboarding_completed", "timezone", "updated_at")
    list_filter = ("approval_mode", "onboarding_completed")
    search_fields = ("user__username", "display_name")
