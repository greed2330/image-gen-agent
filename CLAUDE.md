# image-gen-agent — Claude Code Instructions

> Before any task:
> 1. Read `docs/작업기록/체크리스트.md` — single source of truth for current status and next actions.
> 2. Refer to design docs at `docs/설계문서/00~07` as needed.
> This project is **single-developer (owner) + Claude Code**. Owner makes all final decisions.

## Project Definition
A personal local image generation AI that layers a conversational agent brain on top of local image models (SDXL/Flux family), allowing high-quality image generation through Korean natural language and reference images — NSFW included, fully local.

---

## Document Language Rule

| Document type | Language | Rationale |
|---------------|----------|-----------|
| AI-only documents (CLAUDE.md, prompt.md, any file only agents read) | **English** | Better token efficiency and model parsing accuracy |
| User-facing documents (design docs, checklists, session logs, feedback) | **Korean** | Owner reads and maintains these |
| Conversation with owner | **Korean** | Always |
| Code identifiers, commit message types | **English** | Standard convention |

---

## Four Core Principles (Karpathy)

### 1. Think Before Coding
- State assumptions explicitly before writing any code.
- If a requirement is ambiguous, present interpretations and ask — do not pick one silently.
- If a simpler approach exists than what was asked, say so before proceeding.
- Stop when confused. Name what's unclear and ask rather than guessing.

### 2. Simplicity First
- Write the minimum code that solves the problem. Nothing speculative.
- No abstractions for single-use code.
- No unrequested "flexibility" or "configurability".
- If 50 lines can do what 200 lines do — rewrite it.
- **Test:** Would a senior engineer say this is overcomplicated? If yes, simplify.

### 3. Surgical Changes
- Touch only what the task requires. Nothing else.
- Do NOT "improve" adjacent code, comments, or formatting.
- Do NOT refactor code that isn't broken.
- Match existing style, even if you'd personally do it differently.
- If you notice unrelated dead code — mention it, don't delete it.
- Every changed line must trace directly to the owner's request.

### 4. Goal-Driven Execution
- Before implementing, state a brief plan with verifiable steps:
  ```
  1. [step] → verify: [how to check]
  2. [step] → verify: [how to check]
  ```
- Define success criteria before writing code, not after.
- Loop until verified. Don't stop at "it should work" — confirm it does.

> Source: Andrej Karpathy CLAUDE.md (109K+ stars) / josix/awesome-claude-md curation patterns.

---

## Decision-Making Principles

### 1. Always record the "Why"
Every design decision must include the reason for choosing it AND why alternatives were rejected.
- A decision without "why" will be re-litigated in the next session (this happened multiple times in the initial design session).
- Design docs must have an explicit "Unresolved / Needs Verification" section.
- If adopting the owner's idea, attribute it as "owner's suggestion".
- Bad: "Use Chroma." Good: "Use Chroma — vanilla Flux.1 dev is lightly censored + non-commercial license; Chroma is Apache 2.0 + fully uncensored, strictly better in every dimension."

### 2. Verify, don't assume
License terms, VRAM figures, censorship status, and version info must be confirmed via web search or actual measurement before making decisions.
- Never use "it should be ~" as the basis for a decision.
- Always check the owner's actual environment — assumption failure example: recommended Qwen2.5-VL, but owner already had the newer qwen3-vl:8b.
- The image generation space changes fast. Knowledge past the cutoff date must be supplemented with search.

### 3. Resolve terminology ambiguity first
Before introducing any new tool or technology, check for naming confusion and define terms upfront.
- Examples: "ComfyUI = execution engine (not an AI)", "SD = architecture family (not a product name)", "Flux ≠ Chroma".
- Fuzzy terminology bleeds into fuzzy architecture.

---

## Project-Specific Safety Rules (VRAM)

> Details: `docs/설계문서/02-하드웨어-VRAM-오케스트레이션.md`

- **Single-occupancy rule:** Never load LLM and heavy image model (Flux ~13GB) in VRAM simultaneously.
- **Strict unload order:** Before image generation, **unload LLM (ollama) first**, then submit to ComfyUI. (Known ollama bug: if another program occupies VRAM, unload enters an infinite loop.)
- Unload ollama: API `keep_alive: 0` or `ollama stop <model>`.
- Unload ComfyUI: call `/free` after generation (`{"unload_models": true, "free_memory": true}`).
- Never trust VRAM estimates blindly — measure actual usage for each new model and record it.

## NSFW / Censorship Policy
- Fully local, single personal user — NSFW generation allowed.
- Brain's **prompt synthesis and memory extraction must use uncensored (abliterated/dolphin family) local models**. Censored models refuse NSFW prompts.
- Cloud APIs receive **only censorship-irrelevant tasks**.
- Generated content and personal data must never be committed to the repo (`.gitignore`).

---

## Document Workflow (docs/)

> Structure guide: `docs/기타/README.md`

### Situation → Action

| Situation | Action |
|-----------|--------|
| Starting work | Read `docs/작업기록/체크리스트.md` for current status |
| Task in progress / completed | Update checkboxes and "next actions" immediately (not just at PR time) |
| Large unit completed | Move that block to `docs/작업기록/완료보관/` |
| Mistake / owner correction | Write `docs/기타/피드백/YYYY-MM-DD-topic.md` (what / why / how to avoid) |
| Non-obvious bug resolved | Record in `docs/기타/디버깅기록/` (symptom → cause → fix) |
| Code review performed | Record in `docs/기타/코드리뷰/` |
| External reference consulted | Record in `docs/기타/외부레퍼런스/` |
| Design changed | Update the relevant `docs/설계문서/` file + checklist simultaneously |

- **Work status lives exclusively in `docs/작업기록/체크리스트.md`.** Do not record status elsewhere.
- Feedback docs exist to prevent recurrence. Write them immediately, concisely.

### Session Logs (required at every session end)

**Location**: `docs/작업기록/세션로그/session_NNN-YYYY-MM-DD-주제.md`
- NNN: sequential from 001. Existing `conversation_log.md` = `session_001-2026-06-10-초기설계.md`.
- 주제: one-word summary of the session's core work (e.g. `초기설계`, `환경셋업`, `백엔드코어`).

**Required content** (keep it concise — purpose is context recovery for next session):
```
## 세션 목표
## 주요 결정 (무엇을·왜·버린 대안)
## 산출물 (생성/수정된 파일)
## 미해결 / 다음 세션으로 넘기는 것
```

### Work Unit Definitions (when to leave which document)

| Unit | Trigger | Required document |
|------|---------|-------------------|
| **Session end** | Owner signals end (자러 갈게 / 오늘 여기까지 / wrap up / etc.) | `session_NNN` log + checklist update |
| **Phase complete** | All Phase checklist items `[x]` | Move Phase block to `완료보관/` |
| **Major architecture decision** | New or changed design doc | "Why" + rejected alternatives recorded in design doc |
| **Bug / mistake** | Owner correction or unexpected behavior | `docs/기타/피드백/` written immediately |
| **Model switch (Opus↔Sonnet)** | Just before switching | `prompt.md` updated with instructions for next model |

---

## Coding Rules

### General
- One function, one responsibility. Max 50 lines — if exceeded, split.
- No duplicate logic → extract to service layer.
- No magic numbers or strings → constants or config.
- Comments explain *why*, not *what*.
- Model paths, API keys, ports: never hardcode → `.env` / `config`.

### Language & Framework (confirmed)
- **Backend: Python 3.11+ (FastAPI). Frontend: Next.js + TypeScript. UI: custom-built.**
- Python: type hints required on all functions, consistent `async/await`, specific exceptions only (no bare `except Exception`), import order: stdlib → third-party → local.

### Logging
- Standard `logging` library only. No `print()`.
- Log directory: `logs/` (auto-create on startup, in `.gitignore`).
- Required log points: ollama/ComfyUI connect attempt/success/failure, **VRAM load/unload transitions**, generation request start/complete (with duration), memory extract/search.

### Testing
- New function or endpoint → write test alongside it (not after).
- Happy path + at least one failure case per function.
- **Mock all external dependencies (ollama/ComfyUI/cloud API)** — no live model calls in tests.
- All tests must pass before opening a PR.

### Prototypes / Mockups (versioned)
- Throwaway exploration artifacts (UI mockups, design prototypes, test spikes) live under `mockup/` or `prototypes/`, never in `backend/`/`frontend/`.
- **Never overwrite a previous version.** Each new iteration = a new file with an incremented suffix: `name-v1.html`, `name-v2.html`, … Keep prior versions so the owner can compare side by side.
- In the response, state what changed between versions; add a short comment header at the top of the file noting version + key changes.
- Disposable by nature: not test-covered, excluded from production builds. Real implementation follows the confirmed stack (Python + Next.js), not the mockup's HTML.

---

## Git / Workflow (solo)

- Never push directly to `main`. Work on `feat/*` or `fix/*` branches, then PR.
- **Commit frequently and autonomously — commit at each logical working unit, without waiting for a per-commit request** (owner standing instruction, 2026-06-24). Professional granularity: one logical change per commit, conventional type prefix; never batch unrelated changes into a single commit.
- **Push only when the owner asks** (outward-facing action; commits stay local until then). Commit message types: `feat/fix/refactor/docs/chore`.
- Commit after each working unit. Recommended: ~3 files changed or one logical change, whichever comes first.
- When blocked: stop, record the blocker in the checklist, do not guess.

### On Error
1. Read the full error — not just the first line.
2. Fix minimally. Do not touch unrelated code.
3. Write a test that reproduces the bug, then fix it, then verify the test passes.
4. Unresolved → record in `docs/작업기록/체크리스트.md` as a blocker and stop.

---

## Session-End Self-Review

Run when owner signals end, or just before a PR:
```
□ Read every file you modified top to bottom
□ Does every changed line trace to the owner's request?
□ Any code added "just in case"? → Remove it
□ Any hardcoded values (paths, ports, keys)? → Move to config
□ Any TODO / FIXME / print() / debug statements? → Clean up
□ Re-run tests and confirm they pass
□ Update docs/작업기록/체크리스트.md (check completed items + update next actions)
□ If a mistake was made → write docs/기타/피드백/
□ Write session log: docs/작업기록/세션로그/session_NNN-YYYY-MM-DD-주제.md
```

---

## NEVER
- Commit model files, generated images, or personal data to the repo
- Load LLM and heavy image model in VRAM at the same time
- Write implementation code before language/framework is confirmed (already confirmed: Python + Next.js)
- Hardcode model paths, API keys, or ports
- Use a censored model for NSFW prompt synthesis (it will refuse) / route NSFW tasks to cloud API
- Open a PR without passing tests
- Commit or push without owner's request
- End a session without writing a session log (owner end signal = log trigger)
- Treat unverified assumptions about license terms, VRAM figures, or censorship status as facts
