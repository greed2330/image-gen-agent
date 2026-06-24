"""Tests for WorkflowRouter, ParamResolver, PromptCompiler pipeline stages."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.models.schemas import (
    Intent, ModelProfile, NsfwLevel, RouteDecision, WorkflowType,
)


# --- WorkflowRouter ---

@pytest.mark.asyncio
async def test_workflow_router_defaults_to_txt2img_wai():
    from app.pipeline.workflow_router import WorkflowRouter
    router = WorkflowRouter()
    intent = Intent(identity_tags=["1girl"])
    result = await router.route(intent)
    assert result.workflow == WorkflowType.TXT2IMG
    assert result.model_profile == ModelProfile.ILLUSTRIOUS
    assert "wai" in result.checkpoint.lower()


@pytest.mark.asyncio
async def test_workflow_router_noob_style_hint():
    from app.pipeline.workflow_router import WorkflowRouter
    router = WorkflowRouter()
    intent = Intent(identity_tags=["1girl"], style="noobai style")
    result = await router.route(intent)
    assert result.model_profile == ModelProfile.NOOBAI
    assert "NoobAI" in result.checkpoint


# --- ParamResolver ---

@pytest.mark.asyncio
async def test_param_resolver_illustrious_preset():
    from app.pipeline.param_resolver import ParamResolver
    from app.models.schemas import CompiledPrompt

    resolver = ParamResolver()
    resolver.load_presets()

    intent = Intent(identity_tags=["1girl"])
    route = RouteDecision(
        workflow=WorkflowType.TXT2IMG,
        checkpoint="wai.safetensors",
        model_profile=ModelProfile.ILLUSTRIOUS,
    )
    compiled = CompiledPrompt(positive=["1girl"], negative=[], model_profile=ModelProfile.ILLUSTRIOUS)

    params = await resolver.resolve(intent, route, compiled)

    assert 12 <= params.steps <= 50
    assert 3.0 <= params.cfg <= 9.0
    assert params.resolution.width > 0
    assert params.resolution.height > 0


@pytest.mark.asyncio
async def test_param_resolver_clamps_values():
    """Presets must produce values within hard_clamp bounds."""
    from app.pipeline.param_resolver import ParamResolver
    from app.models.schemas import CompiledPrompt

    resolver = ParamResolver()
    resolver.load_presets()

    for profile in [ModelProfile.ILLUSTRIOUS, ModelProfile.NOOBAI]:
        intent = Intent()
        route = RouteDecision(
            workflow=WorkflowType.TXT2IMG,
            checkpoint="x.safetensors",
            model_profile=profile,
        )
        compiled = CompiledPrompt(positive=[], negative=[], model_profile=profile)
        params = await resolver.resolve(intent, route, compiled)
        assert 12 <= params.steps <= 50, f"{profile} steps out of clamp"
        assert 3.0 <= params.cfg <= 9.0, f"{profile} cfg out of clamp"


# --- PromptCompiler (censored tag stripping) ---

@pytest.mark.asyncio
async def test_prompt_compiler_strips_censored_tags_to_negative():
    from app.pipeline.prompt_compiler import PromptCompiler
    from app.clients.tipo_client import CENSORED_TAGS
    from app.services.tag_allowlist import TagAllowlist

    tipo_mock = AsyncMock()
    # TIPO returns tags including censored ones
    tipo_mock.expand_tags.return_value = [
        "1girl", "nude", "lying", "censored", "mosaic censoring"
    ]

    compiler = PromptCompiler(
        ollama=AsyncMock(),
        tipo=tipo_mock,
        allowlist=TagAllowlist(),  # no CSV loaded → passes all
    )
    compiler.load_presets()

    intent = Intent(identity_tags=["1girl", "nude"], nsfw_level=NsfwLevel.EXPLICIT)
    route = RouteDecision(
        workflow=WorkflowType.TXT2IMG,
        checkpoint="wai.safetensors",
        model_profile=ModelProfile.ILLUSTRIOUS,
    )
    result = await compiler.compile(intent, route)

    # censored tags must NOT appear in positive
    positive_flat = " ".join(result.positive)
    assert "censored" not in positive_flat
    assert "mosaic censoring" not in positive_flat

    # they must appear in negative
    negative_flat = " ".join(result.negative)
    assert "censored" in negative_flat


@pytest.mark.asyncio
async def test_prompt_compiler_preserves_nsfw_tags():
    from app.pipeline.prompt_compiler import PromptCompiler
    from app.services.tag_allowlist import TagAllowlist

    tipo_mock = AsyncMock()
    tipo_mock.expand_tags.return_value = ["1girl", "nude", "explicit", "lying"]

    compiler = PromptCompiler(
        ollama=AsyncMock(),
        tipo=tipo_mock,
        allowlist=TagAllowlist(),
    )
    compiler.load_presets()

    intent = Intent(identity_tags=["1girl", "nude"], nsfw_level=NsfwLevel.EXPLICIT)
    route = RouteDecision(
        workflow=WorkflowType.TXT2IMG,
        checkpoint="wai.safetensors",
        model_profile=ModelProfile.ILLUSTRIOUS,
    )
    result = await compiler.compile(intent, route)

    positive_flat = " ".join(result.positive)
    assert "nude" in positive_flat
    assert "explicit" in positive_flat


# --- Orchestrator._build_workflow ---

def test_build_workflow_fills_slots():
    from app.pipeline.orchestrator import _build_workflow
    from app.models.schemas import CompiledPrompt, GenParams, Resolution

    compiled = CompiledPrompt(
        positive=["1girl", "smile"],
        negative=["censored"],
        model_profile=ModelProfile.ILLUSTRIOUS,
    )
    params = GenParams(
        steps=28, cfg=5.0, sampler="euler_a", scheduler="normal",
        resolution=Resolution(width=832, height=1216),
    )
    route = RouteDecision(
        workflow=WorkflowType.TXT2IMG,
        checkpoint="wai.safetensors",
        model_profile=ModelProfile.ILLUSTRIOUS,
    )
    wf = _build_workflow(compiled, params, route, seed=12345)

    assert wf["3"]["inputs"]["steps"] == 28
    assert wf["3"]["inputs"]["cfg"] == 5.0
    assert wf["4"]["inputs"]["ckpt_name"] == "wai.safetensors"
    assert "1girl" in wf["6"]["inputs"]["text"]
    assert "censored" in wf["7"]["inputs"]["text"]
    assert wf["5"]["inputs"]["width"] == 832
    assert "_comment" not in wf


@pytest.mark.asyncio
async def test_prompt_compiler_protects_identity_from_tipo_conflicts():
    """Seed tags are emphasized; TIPO-injected same-group conflicts go to negative."""
    from app.pipeline.prompt_compiler import PromptCompiler
    from app.services.tag_allowlist import TagAllowlist

    tipo_mock = AsyncMock()
    tipo_mock.expand_tags.return_value = [
        "white hair", "tiger ears", "kemonomimi",   # same as protected — should be skipped
        "black hair", "multicolored hair", "streaked hair",  # hair_color conflict → negative
        "sports bra", "midriff",                    # scene extras → positive
    ]

    compiler = PromptCompiler(
        ollama=AsyncMock(),
        tipo=tipo_mock,
        allowlist=TagAllowlist(),  # no CSV → passes all
    )
    compiler.load_presets()

    intent = Intent(
        identity_tags=["white hair", "tiger ears", "kemonomimi"],
        nsfw_level=NsfwLevel.SAFE,
    )
    route = RouteDecision(
        workflow=WorkflowType.TXT2IMG,
        checkpoint="wai.safetensors",
        model_profile=ModelProfile.ILLUSTRIOUS,
    )
    result = await compiler.compile(intent, route)

    # Protected tags must be emphasized in positive
    assert "(white hair:1.3)" in result.positive
    assert "(tiger ears:1.3)" in result.positive

    # Conflicting hair colors must NOT appear in positive (even unemphasized)
    assert not any("black hair" in t for t in result.positive)
    assert not any("multicolored hair" in t for t in result.positive)
    assert not any("streaked hair" in t for t in result.positive)

    # Conflicting tags must be in negative
    negative_flat = " ".join(result.negative)
    assert "black hair" in negative_flat
    assert "multicolored hair" in negative_flat

    # Scene extras pass through to positive
    assert "sports bra" in result.positive
    assert "midriff" in result.positive


@pytest.mark.asyncio
async def test_prompt_compiler_excludes_user_negated_tags():
    """exclude_tags go to negative; TIPO re-injecting them is stripped from positive."""
    from app.pipeline.prompt_compiler import PromptCompiler
    from app.services.tag_allowlist import TagAllowlist

    tipo_mock = AsyncMock()
    tipo_mock.expand_tags.return_value = [
        "barefoot", "standing",      # wanted scene extras → positive
        "shoes", "socks", "loafers", # TIPO re-injected excluded items → must be dropped
    ]

    compiler = PromptCompiler(ollama=AsyncMock(), tipo=tipo_mock, allowlist=TagAllowlist())
    compiler.load_presets()

    intent = Intent(
        identity_tags=["1girl", "solo"],
        scene_tags=["barefoot"],
        exclude_tags=["shoes", "socks"],
        nsfw_level=NsfwLevel.SAFE,
    )
    route = RouteDecision(
        workflow=WorkflowType.TXT2IMG,
        checkpoint="wai.safetensors",
        model_profile=ModelProfile.ILLUSTRIOUS,
    )
    result = await compiler.compile(intent, route)

    # Excluded tags must not appear in positive even if TIPO re-injected them
    assert not any("shoes" in t for t in result.positive)
    assert not any("socks" in t for t in result.positive)
    # Excluded tags forced into negative
    negative_flat = " ".join(result.negative)
    assert "shoes" in negative_flat
    assert "socks" in negative_flat
    # Wanted scene tag survives
    assert "barefoot" in result.positive


def test_build_workflow_seed_is_injected():
    """Seed passed as argument must appear in workflow node 3."""
    from app.pipeline.orchestrator import _build_workflow
    from app.models.schemas import CompiledPrompt, GenParams, Resolution

    compiled = CompiledPrompt(positive=[], negative=[], model_profile=ModelProfile.ILLUSTRIOUS)
    params = GenParams(
        steps=20, cfg=5.0, sampler="euler_a", scheduler="normal",
        resolution=Resolution(width=1024, height=1024),
    )
    route = RouteDecision(
        workflow=WorkflowType.TXT2IMG,
        checkpoint="x.safetensors",
        model_profile=ModelProfile.ILLUSTRIOUS,
    )
    wf = _build_workflow(compiled, params, route, seed=99999)
    assert wf["3"]["inputs"]["seed"] == 99999


def test_build_workflow_img2img_uses_correct_template():
    """IMG2IMG route: uses img2img.json, sets node 10 image, no node 5 resolution."""
    from app.pipeline.orchestrator import _build_workflow
    from app.models.schemas import CompiledPrompt, GenParams, Resolution

    compiled = CompiledPrompt(positive=["1girl"], negative=[], model_profile=ModelProfile.ILLUSTRIOUS)
    params = GenParams(
        steps=28, cfg=5.0, sampler="euler_ancestral", scheduler="normal",
        resolution=Resolution(width=832, height=1216), denoise=0.55,
    )
    route = RouteDecision(
        workflow=WorkflowType.IMG2IMG,
        checkpoint="wai.safetensors",
        model_profile=ModelProfile.ILLUSTRIOUS,
    )
    wf = _build_workflow(compiled, params, route, seed=42, input_image="ref_abc.png")

    assert wf["10"]["inputs"]["image"] == "ref_abc.png"   # LoadImage node filled
    assert wf["3"]["inputs"]["denoise"] == 0.55           # img2img denoise
    assert wf["3"]["inputs"]["seed"] == 42
    assert "5" not in wf                                  # no EmptyLatentImage
    assert "_comment" not in wf


def test_build_workflow_ipadapter_template():
    """IPADAPTER route: ipadapter.json, reference at node 10, KSampler fed by IPAdapter(13), EmptyLatent kept."""
    from app.pipeline.orchestrator import _build_workflow
    from app.models.schemas import CompiledPrompt, GenParams, Resolution

    compiled = CompiledPrompt(positive=["1girl"], negative=[], model_profile=ModelProfile.ILLUSTRIOUS)
    params = GenParams(
        steps=28, cfg=5.0, sampler="euler_ancestral", scheduler="normal",
        resolution=Resolution(width=832, height=1216), denoise=1.0,
    )
    route = RouteDecision(
        workflow=WorkflowType.IPADAPTER,
        checkpoint="wai.safetensors",
        model_profile=ModelProfile.ILLUSTRIOUS,
    )
    wf = _build_workflow(compiled, params, route, seed=7, input_image="ref_xyz.png")

    assert wf["10"]["inputs"]["image"] == "ref_xyz.png"        # reference loaded
    assert wf["13"]["class_type"] == "IPAdapter"               # apply node present
    assert wf["3"]["inputs"]["model"] == ["13", 0]             # KSampler uses patched model
    assert wf["5"]["inputs"]["width"] == 832                   # EmptyLatentImage filled
    assert "_comment" not in wf


def test_build_workflow_controlnet_template():
    """CONTROLNET route: controlnet.json, reference at node 10, openpose preprocessor, KSampler fed by ControlNetApply(17)."""
    from app.pipeline.orchestrator import _build_workflow
    from app.models.schemas import CompiledPrompt, GenParams, Resolution

    compiled = CompiledPrompt(positive=["1girl"], negative=[], model_profile=ModelProfile.ILLUSTRIOUS)
    params = GenParams(
        steps=28, cfg=5.0, sampler="euler_ancestral", scheduler="normal",
        resolution=Resolution(width=832, height=1216), denoise=1.0,
    )
    route = RouteDecision(
        workflow=WorkflowType.CONTROLNET,
        checkpoint="wai.safetensors",
        model_profile=ModelProfile.ILLUSTRIOUS,
    )
    wf = _build_workflow(compiled, params, route, seed=7, input_image="pose_ref.png")

    assert wf["10"]["inputs"]["image"] == "pose_ref.png"          # reference loaded
    assert wf["14"]["class_type"] == "OpenposePreprocessor"       # preprocessor present
    assert wf["16"]["inputs"]["type"] == "openpose"               # union type set
    assert wf["3"]["inputs"]["positive"] == ["17", 0]             # KSampler uses controlnet conditioning
    assert wf["5"]["inputs"]["width"] == 832
    assert "_comment" not in wf


@pytest.mark.asyncio
async def test_workflow_router_img2img_when_reference_set():
    """Intent with reference + default mode (vary) → IMG2IMG workflow."""
    from app.pipeline.workflow_router import WorkflowRouter

    router = WorkflowRouter()
    intent = Intent(identity_tags=["1girl"], reference="ref_abc.png")
    result = await router.route(intent)
    assert result.workflow == WorkflowType.IMG2IMG


@pytest.mark.asyncio
async def test_workflow_router_reference_mode_branches():
    """reference_mode (UI-selected) picks the workflow when a reference is present."""
    from app.pipeline.workflow_router import WorkflowRouter
    from app.models.schemas import ReferenceMode

    router = WorkflowRouter()
    cases = {
        ReferenceMode.CHARACTER: WorkflowType.IPADAPTER,
        ReferenceMode.POSE: WorkflowType.CONTROLNET,
        ReferenceMode.VARY: WorkflowType.IMG2IMG,
    }
    for mode, expected in cases.items():
        intent = Intent(reference="ref.png", reference_mode=mode)
        assert (await router.route(intent)).workflow == expected

    # No reference → always txt2img, mode ignored
    intent = Intent(reference_mode=ReferenceMode.CHARACTER)
    assert (await router.route(intent)).workflow == WorkflowType.TXT2IMG


@pytest.mark.asyncio
async def test_param_resolver_img2img_denoise():
    """IMG2IMG route uses img2img_denoise preset value."""
    from app.pipeline.param_resolver import ParamResolver
    from app.models.schemas import CompiledPrompt

    resolver = ParamResolver()
    resolver.load_presets()

    intent = Intent(identity_tags=["1girl"])
    route = RouteDecision(
        workflow=WorkflowType.IMG2IMG,
        checkpoint="wai.safetensors",
        model_profile=ModelProfile.ILLUSTRIOUS,
    )
    compiled = CompiledPrompt(positive=["1girl"], negative=[], model_profile=ModelProfile.ILLUSTRIOUS)
    params = await resolver.resolve(intent, route, compiled)
    assert params.denoise == pytest.approx(0.55)
