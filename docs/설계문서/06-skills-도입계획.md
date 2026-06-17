# 06. Skills 도입 계획 (레퍼런스)

> 최종 수정: 2026-06-10
> ⚠️ 이 문서는 **계획만**. 실제 skill 제작/설치는 **모델을 sonnet으로 전환 후** 별도 진행.
> sonnet 작업자는 이 문서를 출발점으로 삼아 조사·설치할 것.

## 목적
UI/UX 설계·구현 품질을 높일 Claude Code skills를 GitHub에서 선별·설치.
설치 위치: `.claude/skills/` (프로젝트 로컬).

## 후보 소스 (2026-06 조사, github star 기준)

| 레포 | 내용 | UI/UX 관련성 |
|------|------|-------------|
| `awesome-design-md` (~71K⭐) | 57개 브랜드 디자인 시스템을 plain markdown으로 제공 | ★ 높음 — 채팅 UI 디자인 톤·컴포넌트 기준 |
| `obra/Superpowers` (~174K⭐ 계열) | 검증된 기법·패턴·도구 종합 skills 라이브러리 | 중 — 워크플로우 일반 |
| `mattpocock` skills (~40K⭐) | "Skills for Real Engineers" (TS/프론트 강함) | ★ 높음 — Next.js/TS 작업 |
| `rohitg00/awesome-claude-code-toolkit` | 35개 curated skills + commands/plugins 모음 | 중 — 큐레이션 진입점 |
| `GetBindu/awesome-claude-code-and-skills` | Claude skills 모음 | 중 — 큐레이션 진입점 |

## sonnet 작업자 지시 (요약)
1. 위 레포들 확인 → 본 프로젝트(대화형 이미지 생성 UI: Next.js+TS, 채팅/갤러리/스트리밍) 에 맞는 skill 선별.
2. 우선순위: ① UI/UX 디자인(awesome-design-md류) ② 프론트 구현(Next.js/TS) ③ 일반 워크플로우.
3. 선별한 skill을 `.claude/skills/`에 설치, 라이선스 확인.
4. 설치 목록·출처·용도를 `docs/기타/외부레퍼런스/skills-설치내역.md`에 기록.
5. 본 문서 하단 "설치 결과"에 최종 반영.

## 제약
- 언어/프레임워크 확정(Python 백엔드 + Next.js 프론트 권장)에 의존. 확정 후 프론트 skill 비중 결정.
- 불필요하게 많이 설치하지 말 것 — 실제 쓸 것만 (Simplicity First).

## 설치 결과
- **2026-06-18 결정: 도입 보류(건너뜀).** 오너 판단 — 현시점 불필요.
  - 근거: 프론트 목업(session_004)을 skills 없이 충분히 진행함. Simplicity First — 실제 필요가 생기면 그때 선별 설치.
  - 재검토 시점: Phase 4 프론트엔드 본구현에서 Next.js/TS 작업 비중이 커질 때.
