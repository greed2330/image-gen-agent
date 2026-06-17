import pytest
from unittest.mock import AsyncMock, MagicMock

from app.models.schemas import GenRequest
from app.pipeline.orchestrator import Orchestrator


def _make_orchestrator(intent, route, compiled, params, critique, comfyui, vram):
    from app.pipeline.intent_parser import IntentParser
    from app.pipeline.workflow_router import WorkflowRouter
    from app.pipeline.prompt_compiler import PromptCompiler
    from app.pipeline.param_resolver import ParamResolver
    from app.pipeline.critic import Critic

    ip = AsyncMock(spec=IntentParser)
    ip.parse.return_value = intent

    wr = AsyncMock(spec=WorkflowRouter)
    wr.route.return_value = route

    pc = AsyncMock(spec=PromptCompiler)
    pc.compile.return_value = compiled

    pr = AsyncMock(spec=ParamResolver)
    pr.resolve.return_value = params

    cr = AsyncMock(spec=Critic)
    cr.evaluate.return_value = critique

    return Orchestrator(ip, wr, pc, pr, cr, vram, comfyui)


@pytest.mark.asyncio
async def test_dry_run_stops_before_comfyui(
    sample_intent, sample_route, sample_compiled, sample_params, mock_comfyui
):
    from app.models.schemas import Critique
    from app.services.vram_manager import VramManager

    vram = AsyncMock(spec=VramManager)
    critique = Critique(passed=True)

    orch = _make_orchestrator(
        sample_intent, sample_route, sample_compiled, sample_params,
        critique, mock_comfyui, vram
    )
    request = GenRequest(message="test", chat_id="test-room")
    result = await orch.run(request, dry_run=True)

    assert result.image_path is None
    assert result.params == sample_params
    mock_comfyui.submit.assert_not_called()
    vram.prepare_for_generation.assert_not_called()


@pytest.mark.asyncio
async def test_stage_limit_1_returns_after_intent(
    sample_intent, sample_route, sample_compiled, sample_params, mock_comfyui
):
    from app.models.schemas import Critique
    from app.services.vram_manager import VramManager

    vram = AsyncMock(spec=VramManager)
    orch = _make_orchestrator(
        sample_intent, sample_route, sample_compiled, sample_params,
        Critique(passed=True), mock_comfyui, vram
    )
    request = GenRequest(message="test", chat_id="test-room")
    result = await orch.run(request, stage_limit=1)

    assert len(result.trace.stages) == 1
    assert "intent" in result.trace.stages[0].name
