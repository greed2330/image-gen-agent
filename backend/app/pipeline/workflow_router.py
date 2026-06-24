import logging

from app.models.schemas import Intent, ModelProfile, ReferenceMode, RouteDecision, WorkflowType

logger = logging.getLogger(__name__)

# Checkpoint filenames as installed in Phase 1
_CHECKPOINT_WAI = "waiNSFWIllustrious_v130.safetensors"
_CHECKPOINT_NOOB = "NoobAI-XL-v1.1.safetensors"

# Reference mode → workflow (Doc 14). No reference → txt2img regardless of mode.
_MODE_WORKFLOW = {
    ReferenceMode.CHARACTER: WorkflowType.IPADAPTER,
    ReferenceMode.POSE: WorkflowType.CONTROLNET,
    ReferenceMode.VARY: WorkflowType.IMG2IMG,
}


class WorkflowRouter:
    """② Decide workflow type and checkpoint from Intent.

    With a reference image, reference_mode (UI-selected) picks the workflow:
    character→IPAdapter, pose→ControlNet, vary→img2img. No reference → txt2img.
    Checkpoint selection: WAI (illustrious) default; NoobAI if intent hints at it.
    """

    async def route(self, intent: Intent) -> RouteDecision:
        if intent.reference:
            workflow = _MODE_WORKFLOW.get(intent.reference_mode, WorkflowType.IMG2IMG)
        elif len(intent.characters) >= 2:
            workflow = WorkflowType.REGIONAL   # multi-character → per-character regions (Doc 15)
        else:
            workflow = WorkflowType.TXT2IMG
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
