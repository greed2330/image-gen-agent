# 설계 세션 대화 기록

> 2026-06-10, Opus 4.8와의 설계 세션. 무엇을·왜 결정했는지 시간순 요약.
> (원문 그대로가 아닌 핵심 정리. 의사결정의 "왜"를 보존하는 것이 목적.)

---

## 세션 목표
오너가 "GPT 이미지 생성처럼 채팅창에서 말/이미지로 대충 설명해도 고품질 이미지를 뽑는, 편의적인 **로컬** 이미지 생성 AI"를 만들고 싶어 함. 설계부터 시작.

---

## 1라운드 — 프로젝트 본질 정립
- **핵심 통찰**: GPT 이미지 생성이 "마법처럼" 느껴지는 건 모델이 아니라 **앞단의 오케스트레이션** 때문. 로컬 모델(SDXL/Flux)도 잘 쓰면 고점은 더 높음. 문제는 그 "잘 쓰는" 과정을 사람이 수동으로 한다는 것.
- → **프로젝트 본질 = 새 이미지 모델을 만드는 게 아니라, 기존 로컬 모델 위에 의도해석·라우팅·프롬프트합성·자기평가 두뇌를 얹는 것.**
- 파이프라인 6단계 분해: ①의도해석 ②워크플로우 라우팅 ③프롬프트 컴파일 ④파라미터 결정 ⑤실행(ComfyUI) ⑥자기평가 Critic.

## 2라운드 — 환경 파악
오너 답변:
- 하드웨어: RTX 4070 Ti SUPER (VRAM 16GB) + RAM 64GB.
- 두뇌: 하이브리드(로컬+클라우드).
- 도메인: 애니/일러 중심 + 범용.
- RAM 64GB 활용처: 모델 캐싱(VRAM 스왑 가속) + 일부 CPU offload.

## 3라운드 — 프로젝트 폴더 + NSFW + 모델 질문
- 오너 요청: NSFW 가능하게 설계(로컬 개인용). "Stable Diffusion보다 나은 게 있나?"
- 폴더 생성: `E:\image-gen-agent` + docs 구조.
- 답변: "SD"는 단일 제품이 아니라 아키텍처 계열. 품질은 **체크포인트**가 결정. 애니/일러+NSFW는 Illustrious/NoobAI(SDXL)가 사실상 표준.

## 4라운드 — 웹 조사 (최신 모델·VRAM·메모리·ollama)
검색으로 검증한 결정:
- 애니 메인: WAI-illustrious / NoobAI (SDXL, ~8GB, NSFW 강력).
- 포토리얼: Chroma(Flux 무검열 포크). 4070 Ti Super "mid-range 적합".
- 비전: Qwen2.5-VL(이후 오너 보유 qwen3-vl:8b로 대체).
- ollama 모델은 기본 검열됨 → NSFW 프롬프트 합성엔 무검열 모델 필요.
- VRAM: SDXL ~8GB, Flux fp8 ~13GB / GGUF Q4 ~7GB, LLM 7–8B ~5–6GB.
- VRAM 충돌 해법(오너 아이디어 채택): 대화 시만 LLM on, 생성 시 off. ollama `keep_alive:0`/`ollama stop`, ComfyUI `/free`. **단 ollama는 타 프로그램이 VRAM 점유 중이면 언로드 버그 → LLM 먼저 내리고 이미지 모델 로드 순서 엄수.**
- 메모리: mem0(하이브리드: 벡터+그래프+에피소드, RAG보다 정확) 자가호스팅.

## 5라운드 — 설계 문서 + CLAUDE.md + skills 계획
오너 지시로 작성:
- docs 구조: 설계문서 / 작업기록(체크리스트 SSOT) / 기타(피드백·디버깅·코드리뷰·외부레퍼런스).
- 설계 문서 00~06 작성.
- CLAUDE.md: `E:\Projects\hana_project\hana_claude\CLAUDE.md`에서 솔로 환경에 맞는 규칙 발췌(멀티에이전트 협업 규칙 제외) + Karpathy 4원칙 + github 고스타 레퍼런스(awesome-claude-md 등) + 이 프로젝트 고유 VRAM 안전규칙/NSFW 방침/docs 워크플로우.
- skills는 06번 문서에 **계획만** 작성(실제 제작은 sonnet 전환 후).

## 6라운드 — ②③ 심화 (프롬프트·파라미터)
오너 질문: 어떤 이미지 AI를 쓰나 / LLM 시스템프롬프트를 포맷에 맞게 짤 수 있나 / 파라미터·그림체를 능동 조정하나.
- 용어 정리: ComfyUI는 실행 엔진(AI 아님), 실제 "이미지 생성 AI"=체크포인트(Illustrious 등).
- 답변을 07번 문서로 작성:
  - ② LLM이 JSON 스키마로 구조화 출력. 태그 순서 규약·품질토큰 프리셋·가중치 문법 주입. **hallucination 방지 위해 danbooru 태그 allowlist로 검증·치환.** Flux는 자연어 별도 프로파일.
  - ③ **LLM은 raw 수치 자유생성 금지.** 모델/그림체 프리셋(저점) + 허용범위 nudge(고점) + 하드클램프(안전). 결정 주체를 항목별 표로 분리.

## 7라운드 — NSFW 모델 무료/검열 확인
오너 질문: WAI/NoobAI, Chroma/Flux가 무검열·무료 맞나?
검색 검증 결과(03 문서 반영):
- WAI/NoobAI: Civitai 무료 + 무검열(danbooru). ✅
- **Chroma: Apache 2.0 + 완전 무검열 + 무료**(FLUX.1-schnell 기반 8.9B). 포토리얼 NSFW는 Chroma로 통일.
- **바닐라 Flux.1 dev: 약하게 검열 + 비상업 라이선스 → 제외.** Chroma가 모든 면에서 우월.

## 8라운드 — 언어/UI/ComfyUI/ollama 확정
오너 질문 4개:
- 언어 → 백엔드 Python(FastAPI) + 프론트 Next.js/TS 확정.
- UI 자체 제작? → **자체 제작 추천**(OSS 포크는 오히려 고생). 템플릿 위에서 시작.
- ComfyUI? → 오너 미보유. 이미지 모델 실행 엔진. **Phase 1에서 신규 설치.** 노드 UI 배울 필요 없음(앱이 API로 조종). 대안 diffusers 검토했으나 ControlNet/IPAdapter 생태계 때문에 ComfyUI 채택.
- `ollama list` 평가:
  - 보유: qwen3:14b(메인), qwen3:4b(경량/워커), qwen3-vl:8b(비전 ✅), nomic-embed-text(임베딩 ✅), qwen2.5-coder:14b(JSON 구조화 강함), gemma4:12b(중복/예비).
  - **전부 검열됨** → NSFW 프롬프트 합성용 무검열 모델 1개만 추가 pull 필요.
  - 비전·임베딩은 이미 보유 → 따로 안 받아도 됨. 03 문서 역할표 갱신.

## 9라운드 — handoff 준비
- 오너가 sonnet 전환 전 인수인계 요청: `prompt.md`(다음 작업 상세) + `conversation_log.md`(이 기록) 작성.
- 확인: `/model`로 전환하면 같은 세션 맥락 유지됨. 단 compaction/새 세션 대비해 두 파일은 영구 기록으로 유효.

---

## 최종 산출물 (이 세션)
- `E:\image-gen-agent\` 폴더 + `CLAUDE.md`
- `docs/설계문서/00~07`
- `docs/작업기록/체크리스트.md`, `prompt.md`, `conversation_log.md`
- `docs/기타/` 구조 + README
- 기억: `image-gen-agent.md` (프로젝트 핵심 결정)

## 다음 단계
1. (sonnet) skills 제작 — 06번 문서 기반
2. 무검열 모델 1개 선정 + pull
3. Phase 1 환경 셋업 (ComfyUI 설치 등)
4. (Opus 권장) Phase 2 아키텍처 구현
