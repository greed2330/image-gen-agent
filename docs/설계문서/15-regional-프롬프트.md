# 15. Regional Prompting (영역별 조건부 프롬프트)

> 상태: 설계 (2026-06-25). 구현 전 오너 확인 필요(§6).
> 관련: 체크리스트 「알려진 한계」(색 바인딩), Doc 09(정체성 보존).

---

## 1. 목표 / 풀려는 문제

태그는 "속성 가방"이라 **속성을 특정 주체에 못 묶는다**(실측 확인):
- "금발 소녀와 흑발 소녀" → 둘 다 흑발로 나옴 (색이 캐릭터에 안 묶임)
- 멀티컬러 헤어(흰 베이스+빨강 브릿지) → 베이스색 미보장

**해결:** 캔버스를 영역으로 나누고 **영역마다 다른 프롬프트**를 조건부로 건다. 왼쪽 영역="금발 트윈테일", 오른쪽="흑발 단발" → 각 캐릭터에 색이 묶인다.

### 범위 (1차)
- ✅ **다중 캐릭터** (같은 화면 2~3명, 캐릭터별 속성 바인딩) — 핵심·고가치
- ❌ **멀티컬러 헤어 베이스색**(한 캐릭터 내 영역) — 훨씬 어렵고(부분영역+포즈 따라 영역 변동) 저가치 → 범위 밖

---

## 2. 메커니즘 (ComfyUI 코어, 추가 설치 없음)

`ConditioningSetAreaPercentage`(조건부를 캔버스 비율 영역에 한정) + `ConditioningCombine`(여러 조건부 병합).

```
캐릭터1 프롬프트 → CLIPTextEncode → SetAreaPercentage(x=0,   w=0.5) ┐
캐릭터2 프롬프트 → CLIPTextEncode → SetAreaPercentage(x=0.5, w=0.5) ┼→ Combine → KSampler.positive
공통/배경  프롬프트 → CLIPTextEncode → (전체 영역, 약한 strength)      ┘
```
- N명 → N개 세로 컬럼(각 width=1/N). 캐릭터 i → area(x=i/N, w=1/N, h=1).
- 공통(배경·count·포즈)은 전체 영역 base 조건부.

## 3. 핵심 설계 — 의도 구조 변경

현재 `identity_tags`는 **하나의 평면 bag**. regional엔 **캐릭터별 그룹**이 필요.

- `Intent`에 `characters: list[list[str]]` 추가 (캐릭터별 태그 그룹). 텍스트 LLM이 입력에서 분리("금발 트윈테일 소녀와 흑발 단발 소녀" → `[["blonde hair","twintails"], ["black hair","short hair"]]`).
- 공통 태그(2girls, 배경, 포즈)는 기존 `identity_tags`/`scene_tags`에 유지 → base 조건부.
- **트리거: `len(characters) >= 2`** 일 때만 regional. 1명/0명 → 기존 txt2img.
- LLM 미분리 시(평면 bag만) → 기존 동작(회귀 없음).

## 4. 워크플로 — 가변 노드 생성

N이 가변이라 **정적 JSON 템플릿 불가** → `_build_workflow`가 노드를 **프로그램으로 생성**(기존 템플릿 방식과 다른 신규 경로):
- base txt2img 골격(KSampler/Checkpoint/Latent/VAE/Save) + 동적 생성한 (CLIPTextEncode + SetAreaPercentage)×N + Combine 체인.
- KSampler.positive ← 최종 Combine. negative는 기존처럼 단일.
- TIPO/compile: 각 캐릭터 그룹을 개별 compile? 또는 그룹별 raw 태그만(TIPO 확장은 공통). → §6 미해결.

## 5. 새 모드? 자동?

- regional은 **레퍼런스와 무관**(텍스트 전용 다중 캐릭터). reference_mode 드롭다운과 별개 축.
- **자동 트리거** 권장: `characters>=2`면 자동 regional. 사용자가 모드 고를 필요 없음(다중 캐릭터는 입력에서 자명).
- 단, 영역 분할이 항상 좋은 건 아님(겹친 구도엔 부적합) → 1차는 세로 균등 분할만, 한계 명시.

## 6. 미해결 / 검증 필요

- [ ] **TIPO 상호작용**: 캐릭터 그룹별로 TIPO 확장? 공통만 확장? 영역 프롬프트엔 확장 태그가 영역 오염 가능 → 실측 필요.
- [ ] **정체성 보호(Doc 09)와의 결합**: 캐릭터 그룹 태그도 emphasis/충돌배타 적용? 그룹 단위로 재적용 필요.
- [ ] **영역 경계 부작용**: 균등 세로 분할 시 인물이 영역 밖으로 나가거나 경계에서 깨짐 — strength/overlap 튜닝.
- [ ] 가변 워크플로 생성 코드 — 노드 번호 충돌 없이 동적 생성(기존 정적 템플릿과 분리).
- [ ] 3명 이상 레이아웃 / 비균등 / 가로 분할은 1차 범위 밖.
- [ ] dry-run으로 의도 분리(`characters`) 정확도 검증 선행.
