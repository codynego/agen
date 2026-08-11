from dataclasses import dataclass


@dataclass(frozen=True)
class AgentIdentity:
    name: str
    network_handle: str
    agent_id: str
    trust_level: str
    capabilities: list[str]


@dataclass(frozen=True)
class TaskAnalysis:
    intent_type: str
    capabilities: list[str]
    location: str
    risk_level: str
    requires_clarification: bool
    task_brief: str
    complexity: str
    user_response: str
