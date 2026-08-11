from typing import Protocol

from .types import AgentIdentity, TaskAnalysis


class ModelGateway(Protocol):
    def analyze_task(self, request_text: str, model: str, identity: AgentIdentity) -> TaskAnalysis: ...
