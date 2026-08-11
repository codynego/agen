from django.contrib import admin

from .models import Agent, AgentActivity, AgentConnection, DataGrant, Task, TaskCandidate, TaskResult, TaskStep, TrustEvent


class AgentActivityInline(admin.TabularInline):
    model = AgentActivity
    extra = 0


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ("name", "network_handle", "agent_id", "kind", "hosting_type", "trust_level", "trust_score", "status", "online")
    list_filter = ("kind", "hosting_type", "trust_level", "verified", "status", "online", "category")
    search_fields = ("name", "network_handle", "agent_id", "slug", "company_name", "endpoint")
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


class TaskStepInline(admin.TabularInline):
    model = TaskStep
    extra = 0


class TaskCandidateInline(admin.TabularInline):
    model = TaskCandidate
    extra = 0


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("task_id", "owner", "personal_agent", "status", "risk_level", "created_at")
    list_filter = ("status", "risk_level", "created_at")
    search_fields = ("task_id", "owner__username", "request_text")
    readonly_fields = ("task_id", "created_at", "updated_at")
    inlines = [TaskStepInline, TaskCandidateInline]


@admin.register(AgentConnection)
class AgentConnectionAdmin(admin.ModelAdmin):
    list_display = ("connection_id", "task", "provider_agent", "status", "auto_approved", "created_at")
    list_filter = ("status", "auto_approved", "created_at")
    search_fields = ("connection_id", "task__task_id", "provider_agent__network_handle")
    readonly_fields = ("connection_id", "created_at", "updated_at")


@admin.register(DataGrant)
class DataGrantAdmin(admin.ModelAdmin):
    list_display = ("grant_id", "connection", "expires_at", "revoked_at")
    readonly_fields = ("grant_id", "created_at")


@admin.register(TaskResult)
class TaskResultAdmin(admin.ModelAdmin):
    list_display = ("result_id", "task", "connection", "created_at", "delivered_at")
    search_fields = ("result_id", "task__task_id", "summary")
    readonly_fields = ("result_id", "created_at")
