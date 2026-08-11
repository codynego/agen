from __future__ import annotations

import logging

from django.conf import settings

from .openai_gateway import ModelGatewayError, OpenAIModelGateway
from .types import AgentIdentity, TaskAnalysis


logger = logging.getLogger(__name__)


class ModelRouter:
    def __init__(self, gateway=None):
        self.gateway = gateway

    @property
    def enabled(self) -> bool:
        return self.gateway is not None

    def analyze_task(self, request_text: str, identity: AgentIdentity) -> TaskAnalysis | None:
        if not self.gateway:
            return None
        try:
            analysis = self.gateway.analyze_task(request_text, settings.AGENT_DEFAULT_MODEL, identity)
            if analysis.complexity == "complex" and settings.AGENT_REASONING_MODEL != settings.AGENT_DEFAULT_MODEL:
                analysis = self.gateway.analyze_task(request_text, settings.AGENT_REASONING_MODEL, identity)
            return analysis
        except ModelGatewayError as exc:
            logger.warning("Model analysis unavailable; using deterministic fallback: %s", exc)
            return None


def get_model_router() -> ModelRouter:
    if settings.AGENT_LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        gateway = OpenAIModelGateway(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            timeout_seconds=settings.AGENT_MODEL_TIMEOUT_SECONDS,
        )
        return ModelRouter(gateway)
    return ModelRouter()
