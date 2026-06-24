from enum import Enum
from typing import Any, Optional
import time

from pydantic import BaseModel, Field


class WorkflowType(str, Enum):
    TXT2IMG = "txt2img"
    IMG2IMG = "img2img"
    INPAINT = "inpaint"
    CONTROLNET = "controlnet"
    IPADAPTER = "ipadapter"
    REGIONAL = "regional"


class ReferenceMode(str, Enum):
    """How to use an attached reference image (UI-selected, see Doc 14).

    character → IPAdapter (keep character look) / pose → ControlNet (keep pose)
    / vary → img2img (whole-image variation). Default vary (safest on mis-pick).
    """
    CHARACTER = "character"
    POSE = "pose"
    VARY = "vary"


class ModelProfile(str, Enum):
    ILLUSTRIOUS = "illustrious"
    NOOBAI = "noobai"
    CHROMA = "chroma"


class NsfwLevel(int, Enum):
    SAFE = 0        # SFW — qwen3:14b handles all
    SUGGESTIVE = 1  # mild — qwen3:14b parses structure, abliterated expands tags
    EXPLICIT = 2    # explicit — abliterated handles full intent parsing


class LoraConfig(BaseModel):
    name: str
    weight: float = 0.7


class Resolution(BaseModel):
    width: int
    height: int


# ① Intent: output of IntentParser
class Intent(BaseModel):
    subjects: list[str] = Field(default_factory=list)
    style: Optional[str] = None
    setting: Optional[str] = None
    mood: Optional[str] = None
    nsfw_level: NsfwLevel = NsfwLevel.SAFE
    reference: Optional[str] = None      # local file path
    reference_mode: ReferenceMode = ReferenceMode.VARY  # set from GenRequest (UI), not the LLM
    workflow_hint: Optional[WorkflowType] = None
    identity_tags: list[str] = Field(default_factory=list)  # WHO (shared/count) — protected, emphasized, TIPO-excluded
    scene_tags: list[str] = Field(default_factory=list)      # WHAT — TIPO expands
    exclude_tags: list[str] = Field(default_factory=list)    # NOT wanted — forced to negative, stripped from positive
    characters: list[list[str]] = Field(default_factory=list)  # per-character tag groups (Doc 15); len>=2 → regional

    @property
    def seed_tags(self) -> list[str]:
        return self.identity_tags + self.scene_tags


# ② RouteDecision: output of WorkflowRouter
class RouteDecision(BaseModel):
    workflow: WorkflowType
    checkpoint: str
    model_profile: ModelProfile
    loras: list[LoraConfig] = Field(default_factory=list)


# ③ CompiledPrompt: output of PromptCompiler (after LLM seed → TIPO → allowlist)
class CompiledPrompt(BaseModel):
    positive: list[str]     # final danbooru tags (TIPO-expanded, allowlist-validated)
    negative: list[str]
    weights: dict[str, float] = Field(default_factory=dict)
    model_profile: ModelProfile
    dropped_tags: list[str] = Field(default_factory=list)   # allowlist rejects logged here


# ④ GenParams: output of ParamResolver
class GenParams(BaseModel):
    steps: int
    cfg: float
    sampler: str
    scheduler: str
    resolution: Resolution
    denoise: float = 1.0


# ⑥ Critique: output of Critic
class Critique(BaseModel):
    passed: bool
    issues: list[str] = Field(default_factory=list)
    retry: bool = False


# Pipeline trace — one entry per stage
class PipelineStage(BaseModel):
    name: str
    input: dict[str, Any]
    output: dict[str, Any]
    elapsed_ms: float


class PipelineTrace(BaseModel):
    stages: list[PipelineStage] = Field(default_factory=list)

    def record(self, name: str, inp: dict, out: dict, start: float) -> None:
        self.stages.append(
            PipelineStage(
                name=name,
                input=inp,
                output=out,
                elapsed_ms=(time.monotonic() - start) * 1000,
            )
        )

    def dump(self) -> str:
        lines = []
        for s in self.stages:
            lines.append(f"[{s.name}] {s.elapsed_ms:.1f}ms")
            lines.append(f"  in : {s.input}")
            lines.append(f"  out: {s.output}")
        return "\n".join(lines)


# Top-level request/result
class HistoryMessage(BaseModel):
    role: str    # "user" | "ai"
    text: str


class GenRequest(BaseModel):
    message: str
    chat_id: str
    history: list[HistoryMessage] = Field(default_factory=list)  # recent prior turns
    reference_image: Optional[str] = None   # base64 or file path
    reference_mode: ReferenceMode = ReferenceMode.VARY  # UI-selected; only meaningful with reference_image


class GenResult(BaseModel):
    image_path: Optional[str]
    params: Optional[GenParams]
    critique: Optional[Critique]
    trace: PipelineTrace
    seed: Optional[int] = None
    generation_id: Optional[str] = None
