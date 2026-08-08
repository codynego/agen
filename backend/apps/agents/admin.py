from django.contrib import admin

from .models import Agent, AgentActivity, TrustEvent


class AgentActivityInline(admin.TabularInline):
    model = AgentActivity
    extra = 0


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ("name", "agent_id", "kind", "hosting_type", "trust_level", "trust_score", "status", "online")
    list_filter = ("kind", "hosting_type", "trust_level", "verified", "status", "online", "category")
    search_fields = ("name", "agent_id", "slug", "company_name", "endpoint")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [AgentActivityInline]


@admin.register(AgentActivity)
class AgentActivityAdmin(admin.ModelAdmin):
    list_display = ("title", "agent", "created_at")
    search_fields = ("title", "detail", "agent__name")


@admin.register(TrustEvent)
class TrustEventAdmin(admin.ModelAdmin):
    list_display = ("event_id", "subject_agent", "source_agent", "category", "outcome", "score_delta", "created_at")
    list_filter = ("category", "outcome", "created_at")
    search_fields = ("event_id", "subject_agent__name", "source_agent__name", "evidence_hash")
    readonly_fields = ("event_id", "created_at")
