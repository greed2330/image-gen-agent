# Next Task Handoff (Sonnet) — 캐릭터 정체성 보존 + 기억 영속화 + img2img

> Written 2026-06-18 by **Opus** (설계 세션). 이전 핸드오프(캐릭터 프리셋)는 **폐기됨**.
> Opus가 설계 문서 3개를 완성품 수준으로 작성. Sonnet은 **추론 없이 문서대로 구현**한다.

---

## 0. 반드시 먼저 읽을 것 (순서대로)
1. `CLAUDE.md` — Surgical / Simplicity First / 하드코딩 금지 / 테스트 동반.
2. `docs/작업기록/체크리스트.md` — 현황 SSOT.
3. **설계 지시서 3종 (이번 작업의 본체):**
   - `docs/설계문서/09-캐릭터-정체성-보존.md`
   - `docs/설계문서/10-대화-기억-영속화-및-일관성.md`
   - `docs/설계문서/11-img2img-워크플로우.md`
   - `docs/설계문서/12-대화-모델-교체.md`
   - `docs/설계문서/13-이미지-다운로드.md`

---

## 1. 왜 이 작업인가 (증거 기반 — 반드시 이해하고 시작)

오너의 핵심 불만: **"백호 수인 소녀"라고 분명히 말해도 정체성이 통째로 사라진다**(테스트 2번: 검은 머리 인간 소녀로 나옴).

`POST /generate/dry-run` trace 실측 결과:
- **① IntentParser는 정상** — 정체성 태그(tiger ears/white hair/kemonomimi)를 제대로 뽑음.
- **③ TIPO가 범인** — 10개 seed를 40개로 부풀리며 (a) `black hair`/`multicolored hair` 같은 **모순 태그 주입**, (b) 인간 몸/의상 태그 ~23개로 정체성 ~10개를 **익사**시킴.

→ 해결: **정체성(WHO)을 TIPO에서 빼고, 강조 가중치로 살리고, 모순 태그는 negative로 차단.**

**폐기된 접근(다시 제안 금지):**
- ❌ **캐릭터 프리셋(수동 태그 고정)** — 프리셋도 TIPO에 똑같이 익사 + 매번 수동 관리 비용. 오너가 명시적으로 거부.
- ❌ **"흰색→주황 색 드리프트" 프레이밍** — 오진. 흰색은 정상 렌더됨(1·3번). 실제 모순은 black/multicolored hair.

---

## 2. 구현 순서 (의존성 있음 — 순서 지킬 것)

1. **09 — 1단계** (prompt_compiler 보호 메커니즘, 스키마 변경 없음) → 빠른 검증
2. **09 — 2단계** (슬롯 분리 identity/scene, `Intent` 스키마 변경, TIPO 장면 전용)
3. **10** (기억 영속화 **SQLite+SQLModel** + 생성기록 테이블 + 캐릭터 카드 누적) — **09-2단계의 identity_tags에 의존**. 배포용 DB(Postgres 등)는 추후 결정, 지금은 SQLite
4. **11** (img2img) — 독립적, 위와 병행/이후 아무 때나
5. **12** (대화 LLM 런타임 교체) — 독립적, 아무 때나
6. **13** (이미지 다운로드 버튼) — 독립적, 소규모

각 단계는 별도 커밋(오너 요청 시). 각 문서 끝 "검증" 절을 통과한 뒤 다음 단계로.

---

## 3. 실행 환경

- **통합 실행**: `E:\image-gen-agent\start-all.bat` 더블클릭 → ollama·ComfyUI·backend·frontend 각 창으로 (로그 실시간). 순수 ASCII(인코딩 안전).
- 백엔드 단독: `E:\image-gen-agent\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000` (글로벌 python은 kgen 없음 → 반드시 venv).
- ollama 11434 (모델 7개 설치됨), ComfyUI 8188(`E:\ComfyUI\venv\Scripts\python.exe main.py`).
- **dry-run 디버깅**: `POST /generate/dry-run` (①~④, ComfyUI 불필요) → trace로 단계별 태그 확인. trace 보기 헬퍼 패턴은 Opus가 사용한 방식 참고(JSON stages 순회).

---

## 4. 주의사항 (유지)

- **하드코딩 금지**: 경로·포트·모델명 → config/yaml.
- **검열 모델로 NSFW 합성 금지** / NSFW 클라우드 라우팅 금지.
- **VRAM**: LLM unload → ComfyUI → /free 순서(vram_manager가 처리, 건드리지 말 것).
- **테스트 동반**: 새 함수/엔드포인트마다 happy + 1 failure. 외부 의존(ollama/ComfyUI/TIPO) mock.
- **allowlist 현재 꺼짐**: `danbooru_tags.csv` 미보유(기동 로그 확인). 09-3단계 전까지 확장 태그 검증 안전망 없음 — 유의.
- **프론트엔드**: `frontend/AGENTS.md` 경고 — 이 Next.js는 학습 데이터와 다름. 코드 수정 전 `node_modules/next/dist/docs/` 확인.
- **커밋/푸시는 오너 요청 시에만.** git 최초 커밋 아직 대기 중.

---

## 5. 보류 (이번 범위 밖)

- **mem0/Qdrant 자동 메모리** — doc 10의 JSON 카드로 당장 필요분 해결. mem0는 방-넘는 전역 취향용으로 나중. 이번에 구현 안 함.
- **IPAdapter / ControlNet** — 레퍼런스를 "캐릭터/포즈로 사용"하는 건 별도 설계(Phase 3, qwen3-vl 분석 필요). doc 11은 "이미지 변형(img2img)"만.
- **Critic 루프** — Phase 3. 현재 `Critique(passed=True)` passthrough.
