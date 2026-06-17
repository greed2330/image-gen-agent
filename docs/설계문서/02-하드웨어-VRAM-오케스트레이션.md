# 02. 하드웨어 & VRAM 오케스트레이션

> 최종 수정: 2026-06-10
> 이 프로젝트에서 가장 까다로운 엔지니어링 포인트. 16GB VRAM 안에서 LLM과 이미지 모델이 싸우지 않게 하는 것이 핵심.

## 하드웨어

| 항목 | 스펙 | 비고 |
|------|------|------|
| GPU | RTX 4070 Ti SUPER | **VRAM 16GB** |
| RAM | 64GB | 모델 캐싱 / CPU offload |
| OS | Windows 11 | |

## VRAM 점유량 (검증된 수치, 2026 기준)

| 모델 | VRAM 사용량 | 비고 |
|------|------------|------|
| SDXL / Illustrious / NoobAI (1024px) | ~6–8GB | 메인. 쾌적 |
| Flux.1 dev (fp8) | ~13GB | 고점. LLM과 동시 불가 |
| Flux GGUF Q4 | ~7GB | 절충안 (품질 약간 손실) |
| Chroma (Flux 무검열, fp8) | ~13GB | 포토리얼 NSFW |
| 메인 두뇌 `qwen3:14b` (Q4) | ~9.3GB | SFW 의도해석. SDXL과 동시 불가 |
| NSFW 합성 `qwen3-abliterated:14b` | ~9GB | 무검열 씨앗 합성(폴백) |
| 경량 두뇌 `qwen3:4b` (Q4) | ~2.5GB | 일상 대화. **SDXL과 공존 가능** |
| 비전 Critic `qwen3-vl-abliterated:8b` | ~6.1GB | 레퍼런스 분석 + NSFW Critic |
| TIPO (200M/500M) | ~0.5–1GB | 프롬프트 합성. LLM과 공존 가능 |

> ⚠️ 위 수치 + Windows 자체 VRAM 점유(~1–1.5GB) + ComfyUI/VAE 오버헤드를 항상 고려 → **실사용 가능치 ~14.5GB**. 실측으로 보정 필요.
> ⚠️ 2026-06-10 갱신: 두뇌를 7–8B → **14B(qwen3:14b 9.3GB)**로 교체(03 문서)하면서 공존 계산이 바뀜. 비전은 6.1GB로 더 가벼워짐. TIPO 신규 추가.

### 실측치 (2026-06-17, Phase 1)

| 항목 | 실측 | 비고 |
|------|------|------|
| idle baseline (Windows + ComfyUI 기동, 모델 미로드) | ~1.65GB | nvidia-smi 기준 |
| SDXL(WAI v13.0) 1024² 생성 중 peak | **8.65GB** | 설계 추정 6–8GB와 일치(상단). 모델 자체 ~7GB |
| `/free`(unload_models+free_memory) 후 | ~1.77GB | baseline 복귀 ✅ — ComfyUI 언로드 정상 |
| 생성 속도 | **8.4–10.5초** | 20 steps, euler, normal. C1 지연 목표 기준점 |
| 메인 두뇌 qwen3:14b 로드 | **11.2GB**(모델 9.6GB+baseline) | 설계 추정 9.3GB과 일치 |
| qwen3:4b 로드 | 4.85GB(모델 3.2GB) | 경량 두뇌 |
| ollama 언로드(keep_alive:0) | baseline 복귀 | **무한루프 없음 ✅** |
| TIPO-500M-ft (GPU, transformers) | +1.25GB(load 후 2.63GB) | short 0.9s / long 1.2s. **CPU는 long 82s라 사용불가 → GPU 필수** |

> **COMPILING 공존(계산):** 두뇌 qwen3:14b(9.6GB) + TIPO(1.25GB) + baseline(1.4GB) ≈ **12.3GB < 16GB**. 컴포넌트 개별 실측 합산이며 동시 로드 합동 실측은 미실시(Phase 2 파이프라인 구현 시 확인). TIPO는 backend venv(torch 2.6.0+cu124)에서 GPU 구동.

> **풀 스왑 사이클 검증됨 (2026-06-17):** qwen3:14b 로드(11.2GB) → keep_alive:0 언로드(1.76GB 복귀) → ComfyUI SDXL 생성(peak 11.1GB) → `/free`(1.7GB 복귀). LLM 먼저 내리는 순서 준수 시 ollama 무한루프 미발생, 시분할 전략 실동작 확인. 최대 점유 ~11.2GB로 16GB 예산 내 안전.

## 동시 점유 가능 조합 (16GB 예산)

| 조합 | 합계 | 가능? |
|------|------|-------|
| SDXL(8) + 경량두뇌 `qwen3:4b`(2.5) | ~10.5GB | ✅ 공존 가능 (경량 두뇌 한정) |
| SDXL(8) + 비전 `qwen3-vl`(6.1) | ~14.1GB | ⚠️ 가능하나 빡빡 (Windows 오버헤드 시 위험) |
| SDXL(8) + 메인두뇌 `qwen3:14b`(9.3) | ~17.3GB | ❌ 불가 — **14B 두뇌는 단독 점유** |
| Chroma/Flux(13) + 무엇이든 | 13+ | ❌ 단독 점유 |
| LLM/VL/TIPO 단독 | 1–9.3GB | ✅ |

→ **결론: "LLM과 이미지 모델은 시분할(time-sharing)로 번갈아 점유"가 기본 전략.** 동시 상주는 **SDXL + `qwen3:4b`(2.5GB)** 조합만 예외 허용. 메인 14B 두뇌·Chroma는 무조건 단독. 안정성 위해 기본은 시분할.

## 오케스트레이션 전략

### 상태 머신

```
[IDLE] ─입력─> [CHATTING] ─"생성"의도─> [COMPILING] ─> [GENERATING] ─완료─> [REVIEW(Critic)] ─> [CHATTING/IDLE]
  │              │                        │                 │                    │
  LLM 언로드     두뇌 LLM 로드            두뇌+TIPO 공존     LLM 전부 언로드      이미지 모델 언로드(/free)
  이미지 언로드  (대화/의도해석)          (씨앗→TIPO 합성)   → 이미지 모델 로드    → 비전 LLM 로드(평가)
                                                            (생성, 단독)         재시도 시 →GENERATING(스왑 왕복)
```

> ⚠️ **두뇌는 한 모델이 아니다.** 1회 사이클에서 VRAM은 단계별로 다른 모델이 점유 → 단순 2분할이 아니라 **다단계 스왑**.
> COMPILING: 두뇌(9.3GB) + TIPO(~1GB) 공존 가능. REVIEW의 비전 모델은 이미지 모델을 내린 뒤 로드.

### 핵심 규칙 (버그 회피 포함)

1. **언로드 순서 엄수**: 이미지 생성 직전, **반드시 LLM을 먼저 내린 뒤** ComfyUI에 작업 제출.
   - 이유: ollama는 *다른 프로그램이 VRAM을 점유 중이면 언로드가 무한루프에 빠지는 알려진 버그*가 있음. ComfyUI가 VRAM을 잡기 전에 LLM부터 비워야 안전.
2. **ollama 언로드 방법**: API 호출 시 `keep_alive: 0` 으로 응답 직후 즉시 언로드, 또는 `ollama stop <model>` 명시 호출.
3. **ComfyUI 언로드 방법**: 생성 완료 후 `/free` 엔드포인트(`{"unload_models": true, "free_memory": true}`) 호출로 VRAM 반납.
4. **RAM 캐싱 활용 (64GB)**: 디스크→RAM 로드는 1회만. 모델 가중치를 RAM에 유지하고 VRAM↔RAM 스왑만 반복 → 모델 전환 시 디스크 재로드 비용 제거. ComfyUI는 기본적으로 모델을 RAM에 캐시함(`--highvram`/기본 동작 확인 필요).
5. **소형 상주 모드(옵션)**: 빠른 응답이 필요한 일상 대화에서는 `qwen3:4b`(~2.5GB)를 상주시키고 SDXL과 공존 허용. 메인 14B 두뇌·무거운 추론·Chroma 사용 시에만 시분할 전환.
6. **TIPO 단계 배치**: TIPO(~1GB)는 합성(COMPILING) 단계에서 두뇌 LLM과 **공존**해도 됨(9.3+1≈10.3GB). 굳이 별도 스왑 불필요.
7. **Critic 재시도 상한**: REVIEW→GENERATING 재진입은 매번 **비전↔이미지 모델 스왑 왕복** 비용 발생. **재시도 최대 N회(예: 2회) 하드 캡** — 무한 스왑 방지. 초과 시 마지막 결과 반환 + 경고.
   - ⚠️ **위상: Critic 루프(⑥)는 Phase 3 선택 기능.** 초기(Phase 1/2)는 생성→사용자 확인 방식. 비전 모델의 결함 탐지 신뢰도·스왑 비용이 검증되기 전엔 코어 흐름에 넣지 않는다. 위 상태머신의 REVIEW는 Phase 3 활성화 시 경로.

### 의사 흐름 (생성 1회)

```python
async def generate(intent):
    await ollama.unload_all()            # 1. LLM VRAM 반납 (먼저!)
    await wait_vram_free(threshold)      # 2. VRAM 비워질 때까지 확인
    workflow = build_workflow(intent)    # 3. ComfyUI 그래프 조립
    result = await comfyui.run(workflow) # 4. 생성
    await comfyui.free(unload=True)      # 5. 이미지 모델 VRAM 반납
    # 6. 필요 시 LLM 재로드(REVIEW/Critic 단계)
    return result
```

## RAM(64GB) 활용 요약

- **모델 캐싱**: 체크포인트(6GB) + LoRA 여러 개 + VAE + ControlNet/IPAdapter를 RAM에 상주 → 전환 지연 최소화.
- **LLM CPU offload(보조)**: 비전 모델 등 큰 모델 일부 레이어를 CPU+RAM으로 offload해 VRAM 압박 완화 (속도 trade-off).
- **여러 후보 동시 생성 버퍼**: 배치 결과 이미지/중간 텐서 캐싱.

## 미해결/검증 필요 항목

- [ ] ComfyUI가 Windows에서 `/free` 후 실제로 VRAM을 깨끗이 반납하는지 실측
- [ ] ollama 언로드 무한루프 버그가 현재 버전에서 재현되는지 확인
- [ ] SDXL + 소형LLM 공존 시 실제 안정 한계 실측
- [ ] Flux fp8 vs GGUF Q4 품질/속도 trade-off 실측

## 관련 문서

- [01-시스템-아키텍처](01-시스템-아키텍처.md)
- [03-모델-선정](03-모델-선정.md)
