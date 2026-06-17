from unittest.mock import AsyncMock

import pytest

from app.clients.cloud_llm_client import CloudLLMClient
from app.clients.comfyui_client import ComfyUIClient
from app.clients.ollama_client import OllamaClient
from app.clients.tipo_client import TipoClient
from app.models.schemas import (
    CompiledPrompt,
    Critique,
    GenParams,
    Intent,
    ModelProfile,
    NsfwLevel,
    Resolution,
    RouteDecision,
    WorkflowType,
)
from app.services.tag_allowlist import TagAllowlist


@pytest.fixture
def mock_ollama():
    m = AsyncMock(spec=OllamaClient)
    return m


@pytest.fixture
def mock_comfyui():
    m = AsyncMock(spec=ComfyUIClient)
    m.submit.return_value = "test-prompt-id"
    m.wait_result.return_value = "/tmp/test_output.png"
    return m


@pytest.fixture
def mock_tipo():
    m = AsyncMock(spec=TipoClient)
    m.expand_tags.return_value = ["1girl", "pink hair", "twintails", "smile", "school uniform"]
    return m


@pytest.fixture
def mock_cloud():
    m = AsyncMock(spec=CloudLLMClient)
    return m


@pytest.fixture
def empty_allowlist():
    a = TagAllowlist()
    # no CSV loaded → passes everything through
    return a


@pytest.fixture
def sample_intent():
    return Intent(
        subjects=["1girl"],
        style="anime",
        seed_tags=["1girl", "pink hair", "twintails"],
        nsfw_level=NsfwLevel.SAFE,
    )


@pytest.fixture
def sample_route():
    return RouteDecision(
        workflow=WorkflowType.TXT2IMG,
        checkpoint="wai-illustrious.safetensors",
        model_profile=ModelProfile.ILLUSTRIOUS,
    )


@pytest.fixture
def sample_compiled():
    return CompiledPrompt(
        positive=["1girl", "pink hair", "twintails", "smile"],
        negative=["worst quality", "low quality"],
        model_profile=ModelProfile.ILLUSTRIOUS,
    )


@pytest.fixture
def sample_params():
    return GenParams(
        steps=28, cfg=5.0, sampler="euler_a", scheduler="normal",
        resolution=Resolution(width=832, height=1216),
    )
