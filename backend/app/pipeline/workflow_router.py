import logging

from app.models.schemas import Intent, ModelProfile, RouteDecision, WorkflowType

logger = logging.getLogger(__name__)

# Checkpoint filenames as installed in Phase 1
_CHECKPOINT_WAI = "waiNSFWIllustrious_v130.safetensors"
_CHECKPOINT_NOOB = "NoobAI-XL-v1.1.safetensors"


class WorkflowRouter:
    """② Decide workflow type and checkpoint from Intent.

    Phase 2 scope: txt2img only. Reference image support added in Phase 3.
    Checkpoint selection: WAI (illustrious) default; NoobAI if intent hints at it.
    """

    async def route(self, intent: Intent) -> RouteDecision:
        workflow = WorkflowType.IMG2IMG if intent.reference else WorkflowType.TXT2IMG
        checkpoint = _CHECKPOINT_WAI
        profile = ModelProfile.ILLUSTRIOUS

        if intent.style and "noob" in intent.style.lower():
            checkpoint = _CHECKPOINT_NOOB
            profile = ModelProfile.NOOBAI

        logger.info(
            "route: workflow=%s checkpoint=%s profile=%s",
            workflow, checkpoint, profile,
        )
        return RouteDecision(
            workflow=workflow,
            checkpoint=checkpoint,
            model_profile=profile,
        )
