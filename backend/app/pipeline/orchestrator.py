import logging
import random
import time
import uuid
from typing import TYPE_CHECKING

from app.clients.comfyui_client import ComfyUIClient
from app.models.schemas import GenRequest, GenResult, PipelineTrace, WorkflowType
from app.pipeline.critic import Critic
from app.pipeline.intent_parser import IntentParser
from app.pipeline.param_resolver import ParamResolver
from app.pipeline.prompt_compiler import PromptCompiler
from app.pipeline.workflow_router import WorkflowRouter
from app.services.vram_manager import VramManager

if TYPE_CHECKING:
    from app.services.chat_store import ChatStore
    from app.services.progress_hub import ProgressHub

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
        store: "ChatStore | None" = None,
        progress_hub: "ProgressHub | None" = None,
    ) -> None:
        self._intent = intent_parser
        self._router = workflow_router
        self._compiler = prompt_compiler
        self._resolver = param_resolver
        self._critic = critic
        self._vram = vram_manager
        self._comfyui = comfyui
        self._store = store
        self._progress_hub = progress_hub

    async def _emit_progress(self, value: int, maximum: int) -> None:
        """Relay one ComfyUI sampling-progress event to connected WS clients."""
        if self._progress_hub is None:
            return
        pct = int(value / maximum * 100) if maximum else 0
        await self._progress_hub.broadcast(
            {"type": "progress", "value": value, "max": maximum, "pct": pct}
        )

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

        # Upload reference image (if any) to ComfyUI input dir; mode (UI-selected) drives routing in ②
        input_image: str | None = None
        if request.reference_image:
            input_image = await self._comfyui.upload_image(request.reference_image)
            intent.reference = input_image
            intent.reference_mode = request.reference_mode

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
            {"identity": intent.identity_tags, "scene": intent.scene_tags},
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
        seed = random.randint(0, 2**31 - 1)
        generation_id: str | None = None
        t_exec_start = time.monotonic()

        await self._vram.prepare_for_generation()
        exec_error: Exception | None = None
        image_path: str | None = None
        try:
            t = time.monotonic()
            workflow = _build_workflow(compiled, params, route, seed, input_image=input_image)
            client_id = uuid.uuid4().hex
            image_path = await self._comfyui.generate(workflow, client_id, self._emit_progress)
            trace.record("⑤ execute", {"workflow_keys": list(workflow.keys())}, {"image_path": image_path}, t)
        except Exception as exc:
            exec_error = exc
        finally:
            await self._vram.release_after_generation()

        # Save generation record (success or failure)
        if self._store and request.chat_id:
            from app.models.db import Generation as GenRecord
            duration_ms = (time.monotonic() - t_exec_start) * 1000
            gen_record = GenRecord(
                room_id=request.chat_id,
                user_message=request.message,
                reference_image=request.reference_image,
                identity_tags=intent.identity_tags,
                scene_tags=intent.scene_tags,
                nsfw_level=intent.nsfw_level.value,
                style=intent.style,
                workflow=route.workflow.value,
                checkpoint=route.checkpoint,
                model_profile=route.model_profile.value,
                positive=compiled.positive,
                negative=compiled.negative,
                steps=params.steps,
                cfg=params.cfg,
                sampler=params.sampler,
                scheduler=params.scheduler,
                width=params.resolution.width,
                height=params.resolution.height,
                denoise=params.denoise,
                seed=seed,
                image_path=image_path,
                duration_ms=duration_ms,
                status="error" if exec_error else "ok",
                error=str(exec_error) if exec_error else None,
            )
            saved = self._store.add_generation(gen_record)
            generation_id = saved.id

        if exec_error:
            raise exec_error

        # ⑥ Critic
        t = time.monotonic()
        critique = await self._critic.evaluate(image_path, compiled.model_dump())
        trace.record("⑥ critic", {"image_path": image_path}, critique.model_dump(), t)

        return GenResult(
            image_path=image_path,
            params=params,
            critique=critique,
            trace=trace,
            seed=seed,
            generation_id=generation_id,
        )


_TEMPLATE_BY_WORKFLOW = {
    WorkflowType.IMG2IMG: "img2img.json",
    WorkflowType.IPADAPTER: "ipadapter.json",
}


def _build_workflow(compiled, params, route, seed: int, input_image: str | None = None) -> dict:
    """Fill workflow template slots with compiled prompt + params.

    Template by route.workflow (Doc 14): img2img.json / ipadapter.json / txt2img.json.
    EmptyLatentImage(5) is used by txt2img and ipadapter; LoadImage(10) by img2img and
    ipadapter (reference). Shared slots (3/4/6/7) are filled identically.
    """
    import json
    from pathlib import Path

    template_name = _TEMPLATE_BY_WORKFLOW.get(route.workflow, "txt2img.json")
    template_path = Path(__file__).parent.parent / "workflows" / template_name
    with template_path.open(encoding="utf-8") as f:
        workflow = json.load(f)

    workflow.pop("_comment", None)

    positive_text = ", ".join(compiled.positive)
    negative_text = ", ".join(compiled.negative)

    workflow["3"]["inputs"]["seed"] = seed
    workflow["3"]["inputs"]["steps"] = params.steps
    workflow["3"]["inputs"]["cfg"] = params.cfg
    workflow["3"]["inputs"]["sampler_name"] = params.sampler
    workflow["3"]["inputs"]["scheduler"] = params.scheduler
    workflow["3"]["inputs"]["denoise"] = params.denoise
    workflow["4"]["inputs"]["ckpt_name"] = route.checkpoint
    workflow["6"]["inputs"]["text"] = positive_text
    workflow["7"]["inputs"]["text"] = negative_text

    uses_empty_latent = route.workflow != WorkflowType.IMG2IMG   # txt2img + ipadapter
    uses_reference = route.workflow in (WorkflowType.IMG2IMG, WorkflowType.IPADAPTER)
    if uses_empty_latent:
        workflow["5"]["inputs"]["width"] = params.resolution.width
        workflow["5"]["inputs"]["height"] = params.resolution.height
    if uses_reference:
        workflow["10"]["inputs"]["image"] = input_image

    return workflow
