import logging

from app.models.schemas import Intent, ModelProfile, RouteDecision, WorkflowType

logger = logging.getLogger(__name__)


class WorkflowRouter:
    """② Decide workflow type and checkpoint from Intent.

    Rules:
    - reference image present → img2img / controlnet / ipadapter
    - no reference → txt2img
    - style=anime/illustration → illustrious or noobai
    - style=photorealistic → chroma
    """

    async def route(self, intent: Intent) -> RouteDecision:
        raise NotImplementedError
