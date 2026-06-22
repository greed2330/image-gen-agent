# 11. img2img 워크플로우

> 작성: 2026-06-18 (Opus 설계) · 구현: Sonnet
> 이 문서는 **구현 지시서**다. Sonnet은 추론 없이 아래 명세 그대로 구현한다.
> 관련: [01-시스템-아키텍처](01-시스템-아키텍처.md), [07 §3-3 워크플로우 라우팅](07-프롬프트-및-파라미터-전략.md)

## 현재 상태 (실측)

- `WorkflowType.IMG2IMG` enum은 존재(`schemas.py:10`)하나 **구현 전무.**
- `WorkflowRouter`는 txt2img만 반환(`workflow_router.py:20`).
- 워크플로 템플릿은 `txt2img.json` 하나뿐.
- `GenRequest.reference_image`(base64)는 프론트엔드에서 전송되나 **백엔드에서 완전히 무시됨.**
- `_build_workflow`(`orchestrator.py:104`)는 txt2img 전용.
- `comfyui_client`에 이미지 업로드 기능 없음. `E:/ComfyUI/input` 디렉터리는 존재 확인됨.

## 이번 문서의 범위 (명확히 한정)

**레퍼런스 이미지 = "이 이미지를 변형한다"(img2img) 한 가지 동작만.** denoise로 변형 강도 조절.

> **범위 밖(나중에 별도 문서):** 같은 레퍼런스라도 "이 캐릭터를 써라"(IPAdapter), "이 포즈를 써라"(ControlNet)는 다른 워크플로우다. 이를 구분하려면 qwen3-vl 분석 단계가 필요(Phase 3 레퍼런스 분석). **이번엔 reference_image가 있으면 무조건 img2img**로 처리한다. 이 단순화를 의도적으로 명시.

## 파이프라인 흐름

```
GenRequest.reference_image (base64)
   │  orchestrator: decode → ComfyUI input 디렉터리에 저장 → filename
   ▼
intent.reference = filename
   │  WorkflowRouter: reference 있으면 → IMG2IMG
   ▼
ParamResolver: denoise = img2img_denoise(프리셋, 기본 0.55)
   ▼
_build_workflow: img2img.json 사용 (LoadImage → VAEEncode → KSampler[denoise] → ...)
   ▼
ComfyUI 제출 (VRAM 순서·/free는 기존 그대로)
```

---

# 구현

## A. `config.py` — 입력 디렉터리

```python
# ComfyUI input directory — must match ComfyUI's own input path
comfyui_input_dir: str = "E:/ComfyUI/input"
```

`.env.example`에 `COMFYUI_INPUT_DIR=E:/ComfyUI/input` 추가.

## B. `comfyui_client.py` — 이미지 업로드

`__init__`에 `self._input_dir = Path(settings.comfyui_input_dir)` 추가. 메서드 추가:

```python
async def upload_image(self, b64: str) -> str:
    """Decode base64 image, write to ComfyUI input dir, return the filename
    to reference in a LoadImage node."""
    import base64, uuid
    data = base64.b64decode(b64)
    filename = f"ref_{uuid.uuid4().hex}.png"
    self._input_dir.mkdir(parents=True, exist_ok=True)
    (self._input_dir / filename).write_bytes(data)
    logger.info("ComfyUI: uploaded reference %s (%d bytes)", filename, len(data))
    return filename
```

> 로컬 동일 머신이라 input 디렉터리 직접 쓰기로 충분(결정론적). ComfyUI가 별도 머신이면 `/upload/image` 멀티파트 API로 교체 필요 — 현재 구성은 로컬이므로 직접 쓰기.
> PNG 확장자로 저장하지만 ComfyUI(PIL)는 내용으로 포맷을 판별하므로 jpg 바이트여도 무방.

## C. 워크플로 템플릿 — `backend/app/workflows/img2img.json` (신규)

txt2img와 노드 번호를 맞추되(3=KSampler, 4=Checkpoint, 6/7=CLIP, 8=VAEDecode, 9=SaveImage), `EmptyLatentImage`(5) 대신 `LoadImage`(10) + `VAEEncode`(11)를 쓴다. 해상도는 소스 이미지에서 옴(width/height 슬롯 없음).

```json
{
  "_comment": "ComfyUI img2img workflow. Slots filled by orchestrator._build_workflow().",
  "10": {
    "class_type": "LoadImage",
    "inputs": { "image": "__INPUT_IMAGE__" }
  },
  "4": {
    "class_type": "CheckpointLoaderSimple",
    "inputs": { "ckpt_name": "__CHECKPOINT__" }
  },
  "11": {
    "class_type": "VAEEncode",
    "inputs": { "pixels": ["10", 0], "vae": ["4", 2] }
  },
  "6": {
    "class_type": "CLIPTextEncode",
    "inputs": { "clip": ["4", 1], "text": "__POSITIVE__" }
  },
  "7": {
    "class_type": "CLIPTextEncode",
    "inputs": { "clip": ["4", 1], "text": "__NEGATIVE__" }
  },
  "3": {
    "class_type": "KSampler",
    "inputs": {
      "model": ["4", 0],
      "positive": ["6", 0],
      "negative": ["7", 0],
      "latent_image": ["11", 0],
      "seed": "__SEED__",
      "steps": "__STEPS__",
      "cfg": "__CFG__",
      "sampler_name": "__SAMPLER__",
      "scheduler": "__SCHEDULER__",
      "denoise": "__DENOISE__"
    }
  },
  "8": {
    "class_type": "VAEDecode",
    "inputs": { "samples": ["3", 0], "vae": ["4", 2] }
  },
  "9": {
    "class_type": "SaveImage",
    "inputs": { "images": ["8", 0], "filename_prefix": "output" }
  }
}
```

## D. `orchestrator.py` — 레퍼런스 업로드 + 빌더 분기

`run()` ① intent 직후에 추가:

```python
# 레퍼런스 이미지가 있으면 ComfyUI input에 업로드하고 intent에 표시
input_image: str | None = None
if request.reference_image:
    input_image = await self._comfyui.upload_image(request.reference_image)
    intent.reference = input_image
```

⑤ execute에서 빌더에 전달:

```python
workflow = _build_workflow(compiled, params, route, input_image=input_image)
```

`_build_workflow` 시그니처/분기 변경:

```python
def _build_workflow(compiled, params, route, input_image: str | None = None) -> dict:
    import json, random
    from pathlib import Path
    from app.models.schemas import WorkflowType

    name = "img2img.json" if route.workflow == WorkflowType.IMG2IMG else "txt2img.json"
    template_path = Path(__file__).parent.parent / "workflows" / name
    with template_path.open(encoding="utf-8") as f:
        workflow = json.load(f)
    workflow.pop("_comment", None)

    positive_text = ", ".join(compiled.positive)
    negative_text = ", ".join(compiled.negative)
    seed = random.randint(0, 2**31 - 1)

    workflow["3"]["inputs"]["seed"] = seed
    workflow["3"]["inputs"]["steps"] = params.steps
    workflow["3"]["inputs"]["cfg"] = params.cfg
    workflow["3"]["inputs"]["sampler_name"] = params.sampler
    workflow["3"]["inputs"]["scheduler"] = params.scheduler
    workflow["3"]["inputs"]["denoise"] = params.denoise
    workflow["4"]["inputs"]["ckpt_name"] = route.checkpoint
    workflow["6"]["inputs"]["text"] = positive_text
    workflow["7"]["inputs"]["text"] = negative_text

    if route.workflow == WorkflowType.IMG2IMG:
        workflow["10"]["inputs"]["image"] = input_image
    else:
        workflow["5"]["inputs"]["width"] = params.resolution.width
        workflow["5"]["inputs"]["height"] = params.resolution.height

    return workflow
```

## E. `workflow_router.py` — 레퍼런스 → IMG2IMG

```python
async def route(self, intent: Intent) -> RouteDecision:
    workflow = WorkflowType.IMG2IMG if intent.reference else WorkflowType.TXT2IMG
    checkpoint = _CHECKPOINT_WAI
    profile = ModelProfile.ILLUSTRIOUS
    if intent.style and "noob" in intent.style.lower():
        checkpoint = _CHECKPOINT_NOOB
        profile = ModelProfile.NOOBAI
    logger.info("route: workflow=%s checkpoint=%s profile=%s", workflow, checkpoint, profile)
    return RouteDecision(workflow=workflow, checkpoint=checkpoint, model_profile=profile)
```

## F. `param_resolver.py` — img2img denoise

상단 `from app.models.schemas import ... WorkflowType` 추가. `resolve()` 말미:

```python
denoise = 1.0
if route.workflow == WorkflowType.IMG2IMG:
    denoise = float(preset.get("img2img_denoise", 0.55))
return GenParams(
    steps=steps, cfg=cfg, sampler=preset["sampler"], scheduler=preset["scheduler"],
    resolution=Resolution(width=res_list[0], height=res_list[1]), denoise=denoise,
)
```

`model_presets.yaml` `illustrious_base`·`noobai_base`에 추가:

```yaml
  img2img_denoise: 0.55   # 0.4=원본 거의 유지, 0.75=많이 변형
```

> **변형 강도 키워드("조금만"/"많이") 연동은 이번 범위 밖** — 기본값 0.55 고정. 추후 IntentParser가 강도 힌트를 뽑아 nudge하는 방식으로 확장(과설계 방지를 위해 지금은 단순 기본값).

## VRAM

기존과 동일. ⑤ execute의 `prepare_for_generation()` / `release_after_generation()` 래핑 그대로. img2img도 LLM unload → ComfyUI 순서 동일하게 적용됨(변경 없음).

## 검증

```
1. dry-run은 ⑤ 전 중단이라 img2img 경로 검증 불가 → 실제 생성으로 검증.
2. 프론트엔드에서 +버튼으로 이미지 첨부 + "이 그림을 밤 배경으로 바꿔줘" 생성
   → verify: 출력이 입력 구도를 유지하며 변형됨(완전 새 그림 아님).
3. 백엔드 로그: "ComfyUI: uploaded reference ref_*.png", route workflow=img2img, denoise=0.55
4. reference_image 없는 일반 요청 → 기존 txt2img 정상 동작(회귀 없음).
5. tests/test_pipeline.py: route IMG2IMG일 때 _build_workflow가 img2img.json 로드 +
   node 10 image=filename + node 3 denoise=preset 값임을 단언. node 5 없음 확인.
```

## 건드리는 파일

`config.py`, `.env.example`, `clients/comfyui_client.py`, `workflows/img2img.json`(신규), `pipeline/orchestrator.py`, `pipeline/workflow_router.py`, `pipeline/param_resolver.py`, `presets/model_presets.yaml`, `tests/test_pipeline.py`
