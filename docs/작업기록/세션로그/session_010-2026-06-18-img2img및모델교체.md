# session_010 — 2026-06-18 — img2img + 모델 교체

## 세션 목표
Doc 11 (img2img 워크플로우), Doc 12 (대화 LLM 런타임 교체) 구현.

## 주요 결정 (무엇을·왜·버린 대안)

### Doc 11: img2img
- **로컬 파일 직접 쓰기 방식** — 동일 머신이므로 `E:/ComfyUI/input/` 직접 write. ComfyUI `/upload/image` REST API는 별도 머신용 — 현재 구성에 불필요
- **`img2img.json` 노드 구조**: LoadImage(10) + VAEEncode(11) = txt2img의 EmptyLatentImage(5) 교체. KSampler(3)/CheckpointLoaderSimple(4)/CLIP(6,7)/VAEDecode(8)/SaveImage(9)는 동일 번호 유지로 `_build_workflow` 공통 코드 최소화
- **denoise 0.55 기본값** — 0.4=원본 거의 유지, 0.75=많이 변형. 0.55는 구도 유지하며 스타일 변형. 강도 키워드 연동은 이번 범위 밖(CLAUDE.md 과설계 방지)
- **`_build_workflow` 분기**: `seed`는 이전 세션(session_009)에서 이미 외부로 추출했으므로 doc 11의 내부 생성 예제는 무시하고 파라미터로 유지

### Doc 12: LLM 교체
- **`runtime_settings.json` JSON 파일** — 재시작에도 유지되는 최소 가변 설정. DB와 분리(도메인 데이터 아님). 서비스 레이어 분리(`services/runtime_config.py`)
- **NSFW 모델 고정(잠금)** — `_ollama_model_for(EXPLICIT)`는 `settings.llm_nsfw_model` 하드 반환. 사용자가 검열 모델로 바꾸면 무검열 원칙 위반. 의도적 잠금
- **임베딩 모델 후보에서 제외** — `*embed*` 포함 모델명 필터. coder/vl은 채팅 가능하므로 남김

## 산출물 (생성/수정된 파일)

**신규 생성:**
- `backend/app/workflows/img2img.json` — ComfyUI img2img 워크플로 템플릿
- `backend/app/services/runtime_config.py` — 런타임 가변 설정(chat_model) JSON 영속화
- `backend/app/api/routes_models.py` — GET /models, PUT /models/chat

**수정:**
- `backend/app/config.py` — `comfyui_input_dir` 추가
- `backend/.env.example` — `COMFYUI_INPUT_DIR` 추가
- `backend/app/clients/comfyui_client.py` — `_input_dir` + `upload_image(b64)` 추가
- `backend/app/clients/ollama_client.py` — `list_models()` 추가
- `backend/app/pipeline/orchestrator.py` — 레퍼런스 업로드(① 직후), `_build_workflow`에 `input_image` 파라미터 + 템플릿 분기
- `backend/app/pipeline/workflow_router.py` — `intent.reference` 있으면 IMG2IMG 라우팅
- `backend/app/pipeline/param_resolver.py` — `WorkflowType` 임포트, IMG2IMG일 때 `img2img_denoise` 적용
- `backend/app/pipeline/intent_parser.py` — `RuntimeConfig` 주입, `_ollama_model_for` 런타임 모델 반환
- `backend/app/presets/model_presets.yaml` — illustrious/noobai 프리셋에 `img2img_denoise: 0.55` 추가
- `backend/app/deps.py` — `runtime_config` 싱글턴, `intent_parser`에 주입, `init_all()`에서 `runtime_config.init()` 호출
- `backend/app/main.py` — `models_router` 등록
- `backend/tests/test_pipeline.py` — img2img 관련 테스트 3개 추가
- `backend/tests/test_clients.py` — `test_ollama_list_models_returns_names` 추가
- `frontend/lib/api.ts` — `listModels()`, `setChatModel()` 추가
- `frontend/app/page.tsx` — Settings 컴포넌트에 모델 드롭다운 추가
- `frontend/app/page.module.css` — `.modelSelect` 스타일 추가

## 검증
- 45 tests passed
- TypeScript 컴파일 오류 없음
- `GET /models` → available 목록 + current (embed 제외 확인)
- `PUT /models/chat {"model":"gemma4:12b"}` → 200, `runtime_settings.json` 갱신
- `PUT /models/chat {"model":"nonexistent"}` → 400 (설치 검증)

## 미해결 / 다음 세션으로 넘기는 것
- 설계 문서 09~13 전부 구현 완료. Opus가 설계한 블록 전체 완료.
- 남은 작업:
  - 생성 진행률 WebSocket 스트리밍 (현재 타이머 시뮬레이션)
  - danbooru_tags.csv 확보 (allowlist 현재 비활성)
  - IPAdapter / ControlNet (Phase 3 — qwen3-vl 분석 선행)
  - mem0/Qdrant 자동 메모리
  - Critic 자기평가 루프
  - git 첫 커밋 (오너 요청 대기)
