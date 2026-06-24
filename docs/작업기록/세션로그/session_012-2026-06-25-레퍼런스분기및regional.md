# session_012 — 2026-06-25 — 태그 디버깅 + Phase 3 (레퍼런스 분기 + regional)

## 세션 목표
session_011 이후 연속. 태그 시스템 결함 디버깅 → Phase 3 레퍼런스 분기 + regional prompting 구현.

## 주요 결정 (무엇을·왜·버린 대안)

### 태그 디버깅 사이드 페이즈 (→ PR #3)
- **멀티컬러 헤어**(브릿지/하이라이트): 의도해석이 "bridge dye" 리터럴(비-danbooru)→TIPO 변질. `multicolored hair`/`streaked hair` 구조태그 추가. 단 베이스색 바인딩은 태그 한계(부분 개선).
- **부정·제외 `exclude_tags`**: "맨발/안경 없이"를 negative로 보내는 경로가 없던 구조적 공백 → `Intent.exclude_tags` 도입(negative 강제 + TIPO 재주입분 strip). 다중 캐릭터 `solo` 오염도 이걸로 해결(범용 도구화).
- **다중 캐릭터 count**: `1girl` 중복→`2girls` 교정 + solo 제거.
- **🔴 .gitignore 소스 누락 버그**: `models/` 패턴이 소스 `backend/app/models/`까지 무시 → `schemas.py`/`db.py`가 한 번도 커밋 안 됨(클론 시 실행 불가). 루트 앵커(`/models/`)로 좁히고 누락 소스 추적. **원격 main도 깨져 있던 걸 발견·수정.**

### Phase 3 레퍼런스 분기 (Doc 14, → PR #4)
- **분기 = 명시적 모드 드롭다운**(오너 제안). 자동분류(A)·qwen3-vl 비전(B) 모두 기각: 말투 오독 0 + 백엔드 단순화 + 모드→워크플로 레지스트리 모듈화.
- **character = IPAdapter + qwen3-vl 태그 보강**: IPAdapter 단독은 특징(귀·꼬리) 약하게 전달 → VL로 레퍼런스 features 추출해 identity 강조. 실측으로 정체성 복원 확인.
- **pose = ControlNet union promax + DWPose**: classic openpose는 애니 골격 검출 실패(실측) → DWPose 채택. `comfyui_controlnet_aux` 설치 + ckpts 모델 수동 다운로드.
- **vary = img2img**(기존).

### Phase 3 regional prompting (Doc 15, → PR #4)
- 다중 캐릭터 색 바인딩 한계 해결. 의도해석 `characters` 그룹 분리 → `len>=2` 자동 REGIONAL → 동적 워크플로 생성(영역별 ConditioningSetAreaPercentage + Combine, 코어 노드 무설치). 실측: 금발/흑발 각자 색 유지.

## 산출물 (생성/수정)
**신규:** `services/reference_tagger.py`, `workflows/ipadapter.json`, `workflows/controlnet.json`, `tests/test_reference_tagger.py`, `tests/test_routes_models.py`(011), Doc 14·15, 본 로그.
**수정:** `schemas.py`(ReferenceMode/WorkflowType.REGIONAL/exclude_tags/characters/reference_mode), `intent_parser.py`(멀티컬러·exclude·count·characters 규칙), `prompt_compiler.py`(exclude), `workflow_router.py`(3모드+regional 분기), `orchestrator.py`(reference_mode 주입·VL 보강·동적 regional 생성), `routes_chat.py`(reference_mode 누락 픽스), 프론트(모드 선택기 UI), 체크리스트.
**환경(레포 외부):** ComfyUI에 `comfyui_controlnet_aux` + DWPose/openpose 모델.

## 검증
- 테스트 59개 통과.
- e2e 실측(이미지): character(정체성 복원), pose(DWPose 포즈 전사), regional(금발+흑발 색 유지), 전 파이프라인 스모크 5/5.
- PR #3·#4 main 머지 완료. 클론 가능 상태 복구.

## 미해결 / 다음 세션
- **품질 변동성(모델 한계)**: pose 전사(DWPose 애니 검출 불안정), 다중캐릭터 색(SD 캐릭터 prior가 색 덮어쓰기). 코드 이상 아님. → IPAdapter weight/ControlNet strength 튜닝 트랙.
- Phase 3 남은 것: inpaint, Critic 자기평가 루프, mem0(전역 메모리).
- 멀티컬러 헤어 베이스색·3+명 비균등 레이아웃 = regional 범위 밖.
- 브라우저 픽셀 검증(모드 드롭다운 렌더) 미실시.
