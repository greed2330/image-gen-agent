import json
import logging
import re

from typing import TYPE_CHECKING

from app.clients.cloud_llm_client import CloudLLMClient
from app.clients.ollama_client import OllamaClient
from app.models.schemas import GenRequest, Intent, NsfwLevel, WorkflowType
from app.services.memory import MemoryService
from app.services.tag_groups import load_tag_groups, merge_identity

if TYPE_CHECKING:
    from app.services.chat_store import ChatStore
    from app.services.runtime_config import RuntimeConfig

logger = logging.getLogger(__name__)

# Clinical framing: asks qwen3:14b to classify, not generate NSFW content.
# Reduces refusal rate on suggestive inputs (doc 07 §1-A, Principle 1).
# /no_think disables qwen3 thinking mode for direct structured output.
_SYSTEM_PROMPT = """/no_think
You extract image generation intent from Korean messages and output JSON with tag arrays (identity / scene / exclude).
Carry over established character identity (species, colors, permanent features) into identity_tags across turns.

Korean-to-danbooru tag translation examples:

Input: "분홍 머리 트윈테일 소녀가 웃으며 서있는 그림"
Output: {"subjects":["1girl"],"style":"anime","setting":null,"mood":"happy","nsfw_level":0,"identity_tags":["1girl","solo","pink hair","twintails"],"scene_tags":["smile","standing"],"workflow_hint":null}

Input: "백호 수인 소녀를 그려줘"
Output: {"subjects":["1girl"],"style":"anime","setting":null,"mood":null,"nsfw_level":0,"identity_tags":["1girl","solo","animal ears","tiger ears","tiger tail","white hair","white fur","white body","kemonomimi"],"scene_tags":[],"workflow_hint":null}

Input: "백호 수인 소녀, 스포츠 브라 입고 브이"
Output: {"subjects":["1girl"],"style":"anime","setting":null,"mood":null,"nsfw_level":1,"identity_tags":["1girl","solo","animal ears","tiger ears","tiger tail","white hair","white fur","white body","kemonomimi"],"scene_tags":["sports bra","v sign","midriff"],"workflow_hint":null}

Input: "늑대 수인 소년, 검은 귀에 꼬리"
Output: {"subjects":["1boy"],"style":"anime","setting":null,"mood":null,"nsfw_level":0,"identity_tags":["1boy","solo","animal ears","wolf ears","wolf tail","black hair","kemonomimi"],"scene_tags":[],"workflow_hint":null}

Input: "하얀 머리에 옆머리만 빨간색으로 브릿지 염색한 소녀"
Output: {"subjects":["1girl"],"style":"anime","setting":null,"mood":null,"nsfw_level":0,"identity_tags":["1girl","solo","white hair","red hair","multicolored hair","streaked hair"],"scene_tags":[],"workflow_hint":null}

Input: "안경 안 쓴 갈색 단발 소녀"
Output: {"subjects":["1girl"],"style":"anime","setting":null,"mood":null,"nsfw_level":0,"identity_tags":["1girl","solo","brown hair","short hair"],"scene_tags":[],"exclude_tags":["glasses"],"workflow_hint":null}

Input: "맨발의 소녀, 신발이랑 양말은 신지 말고"
Output: {"subjects":["1girl"],"style":"anime","setting":null,"mood":null,"nsfw_level":0,"identity_tags":["1girl","solo"],"scene_tags":["barefoot"],"exclude_tags":["shoes","socks"],"workflow_hint":null}

Input: "스포츠 브라랑 스패츠 입은 17세 소녀"
Output: {"subjects":["1girl"],"style":"anime","setting":null,"mood":null,"nsfw_level":1,"identity_tags":["1girl","solo","teen"],"scene_tags":["sports bra","spats","midriff","bare midriff","athletic wear"],"workflow_hint":null}

Input: "해변에서 비키니 입은 여성"
Output: {"subjects":["1girl"],"style":"anime","setting":"beach","mood":null,"nsfw_level":1,"identity_tags":["1girl","solo"],"scene_tags":["bikini","beach","summer"],"workflow_hint":null}

Input: "학교 복도에서 걷는 남녀 학생"
Output: {"subjects":["1boy","1girl"],"style":"anime","setting":"school","mood":null,"nsfw_level":0,"identity_tags":["1boy","1girl","school uniform"],"scene_tags":["hallway","walking","couple"],"workflow_hint":null}

Input: "금발 트윈테일 소녀와 흑발 단발 소녀가 나란히 서 있는 그림"
Output: {"subjects":["2girls"],"style":"anime","setting":null,"mood":null,"nsfw_level":0,"identity_tags":["2girls","multiple girls","blonde hair","twintails","black hair","short hair"],"scene_tags":["standing","side by side"],"exclude_tags":["solo","solo focus"],"workflow_hint":null}

Rules:
- identity_tags: 4-10 tags. species, fur/body color, hair color, eye color, age, permanent features, AND clothing the character "always wears". Protected from TIPO expansion.
- scene_tags: 0-8 tags. pose, action, expression, THIS-request clothing, background, mood. TIPO expands these.
- exclude_tags: 0-6 tags, default []. Things the user explicitly does NOT want ("X 없이", "X 안 한/안 쓴", "X 빼고/말고", "맨발"=no shoes/socks). Put the danbooru tag of the EXCLUDED item here, NEVER in identity/scene. These are forced into the negative prompt.
- Clothing defaults to scene_tags; promote to identity_tags only if the user defines it as permanent ("always wears").
- kemonomimi (수인/반수인): use "animal ears", "{species} ears", "{species} tail", "kemonomimi" — NEVER use the animal name alone
- For colored-fur kemonomimi (백호, 흑표 etc.): always include BOTH hair color AND fur/body color (e.g. "white hair", "white fur", "white body")
- Multi-color hair (브릿지/하이라이트/인너컬러/투톤/그라데이션): emit BOTH colors as "{color} hair" tags PLUS a structure tag — "multicolored hair" + "streaked hair" for highlights/bridge, "colored inner hair" for inner-color, "gradient hair" for gradient. Two distinct colors alone collapse to one; the structure tag is required. NEVER emit a literal "bridge dye" or "highlights".
- nsfw_level: 0=SFW, 1=suggestive(swimwear/sports bra/lingerie/midriff), 2=explicit(nude/sex)
- Multiple same-gender characters: use the COUNT tag ("2girls"/"3girls"/"2boys"), NEVER repeat "1girl"/"1boy", and NEVER include "solo". Mixed gender: "1boy 1girl". Also add "solo" and "solo focus" to exclude_tags (TIPO tends to re-inject them). List each character's attributes (tags cannot bind which character has which — that is expected).
- Carry over prior turn character identity into identity_tags; put only new changes in scene_tags
- workflow_hint: null
- Output ONLY the JSON object, nothing else."""


class IntentParser:
    """① Korean natural language → Intent JSON (seed tags only).

    Routing logic (doc 07 §1-A):
    - SAFE / SUGGESTIVE: qwen3:14b with clinical framing (classify, don't generate)
    - EXPLICIT or if qwen3:14b refuses: escalate to abliterated:14b
    - Complex SFW: optionally route to cloud for quality
    """

    def __init__(
        self,
        ollama: OllamaClient,
        cloud: CloudLLMClient,
        memory: MemoryService,
        store: "ChatStore | None" = None,
        runtime: "RuntimeConfig | None" = None,
    ) -> None:
        self._ollama = ollama
        self._cloud = cloud
        self._memory = memory
        self._store = store
        self._runtime = runtime
        self._groups: dict[str, list[str]] = {}

    def load_groups(self) -> None:
        self._groups = load_tag_groups()

    async def parse(self, request: GenRequest) -> Intent:
        """Parse user message into Intent with rough seed_tags."""
        logger.info("intent_parser: msg=%r", request.message[:80])

        # Build message list: prior turns as context, then current request
        # History gives the LLM enough context to carry over established character traits.
        messages = _build_messages(request)

        primary_model = self._ollama_model_for(NsfwLevel.SAFE)
        raw = await self._ollama.chat(
            model=primary_model,
            messages=messages,
            system=_SYSTEM_PROMPT,
            options={"temperature": 0.1},
        )

        logger.info("intent_parser raw response (first 300): %r", raw[:300])
        data = _extract_json(raw)
        if data is None:
            logger.warning(
                "intent_parser: %s produced unparseable output (len=%d), retrying with abliterated",
                primary_model, len(raw),
            )
            raw = await self._ollama.chat(
                model=self._ollama_model_for(NsfwLevel.EXPLICIT),
                messages=messages,
                system=_SYSTEM_PROMPT,
                options={"temperature": 0.1},
            )
            data = _extract_json(raw)

        if data is None:
            logger.error("intent_parser: both models failed, returning minimal intent")
            return Intent()

        nsfw_level = NsfwLevel(min(int(data.get("nsfw_level", 0)), 2))

        # If main model parsed an explicit request, re-run with abliterated for better tags
        if nsfw_level == NsfwLevel.EXPLICIT:
            raw2 = await self._ollama.chat(
                model=self._ollama_model_for(NsfwLevel.EXPLICIT),
                messages=messages,
                system=_SYSTEM_PROMPT,
                options={"temperature": 0.1},
            )
            data2 = _extract_json(raw2)
            if data2:
                data = data2

        workflow_hint = data.get("workflow_hint")
        wf = WorkflowType(workflow_hint) if workflow_hint in WorkflowType._value2member_map_ else None

        # Support both new format (identity_tags/scene_tags) and legacy (seed_tags)
        identity_tags = data.get("identity_tags") or data.get("seed_tags", [])
        scene_tags = data.get("scene_tags", [])

        intent = Intent(
            subjects=data.get("subjects", []),
            style=data.get("style"),
            setting=data.get("setting"),
            mood=data.get("mood"),
            nsfw_level=nsfw_level,
            workflow_hint=wf,
            identity_tags=identity_tags,
            scene_tags=scene_tags,
            exclude_tags=data.get("exclude_tags", []),
        )
        logger.info(
            "intent: nsfw=%s identity=%s scene=%s exclude=%s",
            intent.nsfw_level, intent.identity_tags, intent.scene_tags, intent.exclude_tags,
        )

        # Merge identity into room's character card (accumulates across turns)
        if self._store and request.chat_id and self._groups:
            prev = self._store.get_identity(request.chat_id)
            merged = merge_identity(prev, intent.identity_tags, self._groups)
            intent.identity_tags = merged
            self._store.set_identity(request.chat_id, merged)

        return intent

    def _ollama_model_for(self, level: NsfwLevel) -> str:
        from app.config import settings
        if level == NsfwLevel.EXPLICIT:
            return settings.llm_nsfw_model          # fixed — NSFW policy: must be abliterated
        if self._runtime is not None:
            return self._runtime.get_chat_model()   # user-selected
        return settings.llm_main_model


def _build_messages(request: GenRequest) -> list[dict]:
    """Build the ollama messages array including recent history for context.

    Format: prior user turns interleaved as user messages so the LLM can see
    what character/scene has been established in this chat session.
    Only user-side text is included — AI responses are omitted to keep token count low.
    Cap at last 6 history items to stay within context limits.
    """
    messages: list[dict] = []
    for h in request.history[-6:]:
        if h.role == "user" and h.text.strip():
            messages.append({"role": "user", "content": h.text})
        # AI responses are omitted — the LLM only needs user intent history
    messages.append({"role": "user", "content": request.message})
    return messages


def _extract_json(text: str) -> dict | None:
    """Extract first valid JSON object from LLM output.

    Handles: qwen3 <think>...</think> blocks, markdown fences, leading prose.
    Uses brace-depth tracking to find the outermost complete { } object.
    """
    # Strip qwen3 thinking blocks first (they may contain JSON-like fragments)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # Strip markdown fences
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = text.strip()

    # Try direct parse first (clean JSON response)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Brace-depth scan: find first { ... } with matching depth
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        depth = 0
        for j, c in enumerate(text[i:], i):
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[i : j + 1]
                    try:
                        result = json.loads(candidate)
                        if isinstance(result, dict):
                            return result
                    except json.JSONDecodeError:
                        break
    return None
