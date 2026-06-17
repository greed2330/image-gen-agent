# 다음 작업 지시 (Sonnet handoff — 코드 스켈레톤)

> 작성: 2026-06-10 (Opus, 설계 확정 후). 같은 세션 내 Sonnet 전환 전제.
> 작업: **백엔드 스켈레톤 타이핑.** 아키텍처는 확정됨 — 아래 명세대로 옮기면 됨. 임의 변경 금지, 의문 생기면 멈추고 오너에게.

---

## 0. 시작 전 필수 읽기

1. `CLAUDE.md` — 작업 규칙. 특히 Simplicity First / Surgical / 하드코딩 금지 / 테스트 동반.
2. `docs/설계문서/01-시스템-아키텍처.md` — 6단계 파이프라인.
3. `docs/설계문서/07-프롬프트-및-파라미터-전략.md` — §1-A 합성 파이프라인(LLM 씨앗→TIPO→allowlist)이 핵심.
4. `docs/설계문서/03-모델-선정.md` — 모델·TIPO 배정.
5. `docs/작업기록/세션로그/session_002-2026-06-10-NSFW설계심화.md` — 결정 맥락.

---

## 1. 만들 구조 (확정)

```
backend/
  app/
    main.py                # FastAPI 진입점, 라우트 등록
    config.py              # .env 로드 (포트·모델명·경로). 하드코딩 금지
    api/
      routes_generate.py   # POST /generate, WS /progress
      routes_chat.py       # 채팅방 CRUD
    pipeline/
      orchestrator.py      # 전체 흐름 ①→⑥ 조립 + PipelineTrace 생성
      intent_parser.py     # ① 한국어 → Intent
      workflow_router.py   # ② 워크플로우/체크포인트 라우팅
      prompt_compiler.py   # ③ LLM 씨앗 → TIPO → allowlist
      param_resolver.py    # ④ 프리셋 + nudge + clamp
      critic.py            # ⑥ 비전 평가 루프
    clients/
      ollama_client.py     # 로컬 LLM/VL
      comfyui_client.py    # ComfyUI HTTP + 그래프 제출 + /free
      cloud_llm_client.py  # 클라우드 API
      tipo_client.py       # TIPO 호출
    services/
      vram_manager.py      # 언로드 순서(LLM 먼저 → 이미지 모델)
      memory.py            # mem0 래퍼
      tag_allowlist.py     # danbooru CSV 검증/치환
    models/
      schemas.py           # pydantic 데이터 계약 (§2) — 진짜로 채움
    presets/
      model_presets.yaml   # 07 §3-1
      style_presets.yaml   # 07 §3-2
    workflows/
      txt2img.json         # 템플릿 그래프
    logging_config.py      # 표준 logging, logs/ 자동생성
  cli/
    chat.py                # 대화형 REPL (메모리 유지 확인)
    trace.py               # 요청 1개 → 전 단계 I/O 덤프
    memcheck.py            # 멀티턴 → mem0 회수 검증
  tests/
  .env.example
  requirements.txt
```

---

## 2. 데이터 계약 (schemas.py — 먼저 확정)

pydantic 모델로. 이게 레이어 간 인터페이스라 가장 중요.

```
Intent          : subjects, style, setting, mood, nsfw_level(int/enum),
                  reference(optional), workflow_hint, seed_tags[list]   # 씨앗만
RouteDecision   : workflow(enum: txt2img/img2img/inpaint/controlnet/ipadapter),
                  checkpoint, loras[list]
CompiledPrompt  : positive[list](TIPO+allowlist 통과 최종), negative[list],
                  weights(dict), model_profile
GenParams       : steps, cfg, sampler, scheduler, resolution(tuple), denoise
Critique        : passed(bool), issues[list], retry(bool)
GenRequest      : (사용자 입력 + 채팅방 id + 첨부 이미지)
GenResult       : image_path, params, critique, trace
PipelineTrace   : stages[list of {name, input, output, elapsed_ms}]
```

---

## 3. 스켈레톤 범위 (중요 — 과하게 만들지 말 것)

- `schemas.py`: **완전히 구현.**
- 그 외 모든 모듈: **타입힌트 + docstring + 스텁**(`raise NotImplementedError` 또는 mock 반환).
- `presets/*.yaml`: 07 §3 예시값으로 채워둠.
- `txt2img.json`: 빈 템플릿 또는 최소 골격 (ComfyUI 미설치라 실측은 Phase 1).
- 테스트: 각 단계 스텁에 happy-path + 실패 1개, **외부 의존 전부 mock.**

---

## 4. CLI 디버그 하버스 (오너 요청 — 필수)

우리(에이전트)가 Bash로 직접 돌려 단계별 디버깅하기 위함. 프론트 없이 두뇌 검증.

- **orchestrator는 `PipelineTrace`를 항상 생성** — 각 단계 입력/출력/소요시간 기록.
- `trace.py`: 요청 1개 실행 → 트레이스 펼쳐 출력. ③에서 씨앗→TIPO→allowlist 변환 가시화, ⑤에서 ComfyUI payload 확인.
- `chat.py`: 대화형 REPL. 같은 채팅방에서 턴 이어가며 mem0 유지 확인.
- `memcheck.py`: 멀티턴 시나리오 → 기억 저장·회수 검증.
- 필수 플래그: `--dry-run`(⑤ 직전까지, ComfyUI 없이), `--stage N`(N단계까지), 클라이언트 mock 주입 가능.
- → ComfyUI/이미지모델 설치 전에도 ①~④ 두뇌 로직을 mock으로 검증 가능해야 함.

---

## 5. 작업 순서 (제안)

1. `requirements.txt` + `config.py` + `logging_config.py` + `.env.example`
2. `models/schemas.py` (계약 먼저)
3. `clients/*` 스텁 (인터페이스만)
4. `pipeline/*` 스텁 + `orchestrator.py`(트레이스 골격)
5. `services/*` 스텁
6. `api/*` + `main.py` (POST /generate가 orchestrator 호출하는 배선)
7. `cli/*` (trace.py부터 — 제일 쓸모)
8. `presets/*.yaml`, `workflows/txt2img.json`
9. `tests/` (단계별 mock 테스트)

> 각 단계 후 동작 확인. 커밋은 오너 요청 시에만. 막히면 체크리스트에 블로커 기록 후 멈춤.

---

## 6. 절대 규칙 (CLAUDE.md 발췌)

- 스켈레톤이니 **스텁 이상 구현 금지** (Simplicity First). 살은 Phase 2에서.
- 경로·포트·모델명 하드코딩 금지 → `config.py`.
- `print()` 금지 → logging. 단 `cli/`는 사용자 대면 출력이라 예외 허용.
- 외부 의존(ollama/ComfyUI/cloud/TIPO) 실제 호출하는 테스트 금지 → mock.
- 세션 종료 시 session_003 로그 작성.
