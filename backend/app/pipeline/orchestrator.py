import logging
import time

from app.clients.comfyui_client import ComfyUIClient
from app.models.schemas import GenRequest, GenResult, PipelineTrace
from app.pipeline.critic import Critic
from app.pipeline.intent_parser import IntentParser
from app.pipeline.param_resolver import ParamResolver
from app.pipeline.prompt_compiler import PromptCompiler
from app.pipeline.workflow_router import WorkflowRouter
from app.services.vram_manager import VramManager

logger = logging.getLogger(__name__)


class Orchestrator:
    """Wires the 6-stage pipeline and produces a PipelineTrace for every run.

    dry_run=True stops before ComfyUI submission (stage ⑤).
    Use dry_run to test stages ①–④ without a GPU/image model.
    stage_limit=N stops after stage N (1=intent … 4=params).
    """

    def __init__(
        self,
        intent_parser: IntentParser,
        workflow_router: WorkflowRouter,
        prompt_compiler: PromptCompiler,
        param_resolver: ParamResolver,
        critic: Critic,
        vram_manager: VramManager,
        comfyui: ComfyUIClient,
    ) -> None:
        self._intent = intent_parser
        self._router = workflow_router
        self._compiler = prompt_compiler
        self._resolver = param_resolver
        self._critic = critic
        self._vram = vram_manager
        self._comfyui = comfyui

    async def run(
        self,
        request: GenRequest,
        dry_run: bool = False,
        stage_limit: int | None = None,
    ) -> GenResult:
        trace = PipelineTrace()

        # ① Intent
        t = time.monotonic()
        intent = await self._intent.parse(request)
        trace.record("① intent", {"message": request.message}, intent.model_dump(), t)
        if stage_limit == 1:
            return GenResult(image_path=None, params=None, critique=None, trace=trace)

        # ② Route
        t = time.monotonic()
        route = await self._router.route(intent)
        trace.record("② route", intent.model_dump(), route.model_dump(), t)
        if stage_limit == 2:
            return GenResult(image_path=None, params=None, critique=None, trace=trace)

        # ③ Compile (LLM seed → TIPO → allowlist)
        t = time.monotonic()
        compiled = await self._compiler.compile(intent, route)
        trace.record(
            "③ compile",
            {"seed_tags": intent.seed_tags},
            {**compiled.model_dump(), "dropped": compiled.dropped_tags},
            t,
        )
        if stage_limit == 3:
            return GenResult(image_path=None, params=None, critique=None, trace=trace)

        # ④ Params
        t = time.monotonic()
        params = await self._resolver.resolve(intent, route, compiled)
        trace.record("④ params", route.model_dump(), params.model_dump(), t)
        if stage_limit == 4 or dry_run:
            logger.info("dry_run: stopping before ComfyUI submission")
            return GenResult(image_path=None, params=params, critique=None, trace=trace)

        # ⑤ Execute
        logger.info("VRAM: preparing for generation")
        await self._vram.prepare_for_generation()
        try:
            t = time.monotonic()
            workflow = _build_workflow(compiled, params, route)
            prompt_id = await self._comfyui.submit(workflow)
            image_path = await self._comfyui.wait_result(prompt_id)
            trace.record("⑤ execute", {"workflow_keys": list(workflow.keys())}, {"image_path": image_path}, t)
        finally:
            await self._vram.release_after_generation()

        # ⑥ Critic
        t = time.monotonic()
        critique = await self._critic.evaluate(image_path, compiled.model_dump())
        trace.record("⑥ critic", {"image_path": image_path}, critique.model_dump(), t)

        return GenResult(image_path=image_path, params=params, critique=critique, trace=trace)


def _build_workflow(compiled, params, route) -> dict:
    """Assemble ComfyUI workflow JSON from compiled prompt + params.
    Reads template from app/workflows/ and fills slots.
    """
    raise NotImplementedError
