# 08. NSFW 시드 매핑 & 장면 프리셋 (가설 기반)

> 최종 수정: 2026-06-10
> 07 §1-A "A 레이어 SFW/NSFW 분리"의 실무 부품. **거대 수동 사전이 아니라 경량 시드.**
> ⚠️ TIPO NSFW 품질이 **미실측**이라, 이 문서는 단정이 아니라 **가설 → Phase 2 검증** 구조로 작성한다.

## 0. 위상 (왜 거대 사전이 아닌가)

session_001/002 원래 아이디어는 "danbooru NSFW 태그를 카테고리별로 시스템 프롬프트에 통째로 박기"였다. TIPO 도입(07 §1-A) 후 **어휘·조합·정렬은 TIPO가 가져감** → 거대 사전 불필요.

하지만 TIPO가 **못 하는 것**이 08의 존재 이유:
- TIPO는 한국어를 못 읽고 "이해"도 못 함 — 이미 있는 **영어 danbooru 씨앗을 통계적으로 확장**만 함.
- 따라서 **"한국어 NSFW 발화 → 영어 씨앗 태그"** 변환은 여전히 A 레이어의 몫 (07 §1-A: `qwen3:14b` 임상 분류 우선 → 거부 등급만 `abliterated` 폴백).
- 08 = 그 변환을 돕는 **경량 시드 + 모호 요청 완충 프리셋**. TIPO와 중복 아님(앞단 보완).

---

## 1. 이 문서를 떠받치는 가설 (Phase 2 검증 대상)

> 아래 §2·§3의 분량·형태는 모두 이 가설들에 종속. 가설이 깨지면 분량을 재조정한다.

| ID | 가설 | 검증 방법 (Phase 2) | 깨질 때 대응 |
|----|------|---------------------|--------------|
| **H1** | TIPO는 danbooru 학습이라 **핵심 씨앗 몇 개만** 주면 연관 NSFW 태그를 알아서 확장한다. | 씨앗 3개 vs 10개 입력 → TIPO 출력 풍부도·정확도 비교 | 확장 빈약 시 §2 매핑을 **확대**(중간→상세) |
| **H2** | 저능 `abliterated:14b`는 한국어 NSFW 은어/체위 용어를 정확한 danbooru 태그로 **신뢰성 있게 못 옮긴다.** | 매핑 주입 전/후 allowlist 적중률 비교 | 적중률 낮으면 매핑을 **few-shot 강제**로 승격 |
| **H3** | "야한 거" 같은 빈약 입력은 씨앗이 안 나와 TIPO도 확장할 게 없다. | 모호 입력 시 프리셋 유무 결과 차 | 프리셋 부족 시 §3 세트 **추가** |
| **H4** | 이 문서의 태그 표기(공백/언더스코어·괄호 이스케이프)가 TIPO·체크포인트와 **일치**한다. | Phase 1 표기 실측 (07 §1-A ⚠️ 연결) | 불일치 시 ComfyUI 노드/전처리로 정규화 |

**현재 채택 분량 = 중간 (카테고리당 핵심 10~15, 프리셋 6개).** 근거: H1이 참이면 이것도 과할 수 있고, H1이 거짓이면 모자람. 중간은 "양방향 재조정"의 출발점으로 가장 싸다.

---

## 2. 한국어 → 씨앗 태그 매핑 (H1·H2)

> 형식: `한국어 트리거(들) → danbooru 씨앗 태그`. **씨앗만** 적는다(연관 확장은 TIPO 몫 — H1).
> 표기는 공백 구분(SDXL 관례). 언더스코어 변환은 코드/노드가 처리(H4).
> 한 트리거에 복수 태그를 둔 경우, A 레이어는 맥락에 맞는 것을 고르거나 함께 출력.

### 2-1. 체위 / 포즈
| 한국어 | 씨앗 태그 |
|--------|-----------|
| 정상위 | `missionary` |
| 후배위 / 뒤에서 | `doggystyle`, `from behind` |
| 기승위 / 위에 올라탐 | `girl on top`, `cowgirl position` |
| 역기승위 | `reverse cowgirl position` |
| 측위 / 옆으로 누워 | `spooning` |
| 입위 / 서서 | `standing sex` |
| 다리 벌림 | `spread legs` |
| 다리 들기 | `leg up`, `legs up` |
| 다리 감기 | `leg lock` |
| 네발 자세 | `all fours` |
| 깔고 앉기 / 올라탐 | `straddling` |
| 무릎 꿇기 | `kneeling` |

### 2-2. 행위 / 접촉
| 한국어 | 씨앗 태그 |
|--------|-----------|
| 성교 / 삽입 | `sex`, `vaginal`, `penetration` |
| 구강 (남) | `fellatio`, `oral` |
| 구강 (여) | `cunnilingus` |
| 손 자극 | `fingering`, `handjob` |
| 가슴 | `paizuri` |
| 항문 | `anal` |
| 자위 | `masturbation` |
| 키스 | `kiss`, `french kiss` |
| 애무 / 주무름 | `groping`, `breast grab` |
| 묶기 / 구속 | `bondage`, `bound` |

### 2-3. 의상 상태
| 한국어 | 씨앗 태그 |
|--------|-----------|
| 벗는 중 | `undressing` |
| 가슴 노출 | `breasts out`, `clothing aside` |
| 치마 들춤 | `skirt lift`, `clothes lift` |
| 풀어헤침 | `open clothes`, `open shirt` |
| 상의 탈의 | `topless` |
| 하의 탈의 | `bottomless` |
| 속옷만 | `underwear only`, `lingerie` |
| 옷 입은 채 | `clothed sex`, `clothed female nude male` |
| 비침 / 젖음 | `see-through`, `wet clothes` |
| 완전 나체 | `nude`, `completely nude` |

### 2-4. 표정 / 반응
| 한국어 | 씨앗 태그 |
|--------|-----------|
| 황홀 / 절정표정 | `ahegao` |
| 홍조 | `blush` |
| 눈물 | `tears` |
| 절정 | `orgasm` |
| 혀 내밀기 | `tongue out` |
| 눈 풀림 | `half-closed eyes`, `rolling eyes` |
| 신음 / 입벌림 | `moaning`, `open mouth` |
| 부끄러움 | `embarrassed` |
| 땀 | `sweat` |
| 침 / 체액(입) | `saliva` |

### 2-5. 신체 강조 / 노출
| 한국어 | 씨앗 태그 |
|--------|-----------|
| 큰 가슴 | `large breasts`, `huge breasts` |
| 작은 가슴 | `small breasts`, `flat chest` |
| 엉덩이 강조 | `ass`, `huge ass` |
| 허벅지 | `thighs`, `thick thighs` |
| 잘록한 허리 | `narrow waist` |
| 유두 | `nipples` |
| 음부 | `pussy` |
| 체액 | `cum`, `pussy juice` |

### 2-6. 금지 시드 (allowlist 차단 — 절대 제외)
> 안전·품질 양면. A 레이어가 실수로 출력해도 §C allowlist에서 **하드 드롭**.
- 미성년/연령 퇴행 계열: `loli`, `shota`, `child`, `toddlercon`, `age regression` 등 → **무조건 제거**.
- 본 프로젝트는 성인 가상 캐릭터 한정. 실존 인물·미성년 묘사는 설계상 비대상.

---

## 3. 장면 프리셋 세트 (H3 — 모호 요청 완충)

> "야한 거", "꼴리게" 같은 빈약 입력은 씨앗이 안 나옴 → TIPO도 확장할 게 없음.
> 프리셋 = **모호 입력 시 A 레이어가 고르는 기본 씨앗 묶음.** 사용자가 구체화하면 §2 매핑이 덮어씀.
> 인물수·시점 등 기본 골격만. 나머지는 TIPO 확장 + 스타일 프리셋(07 §3-2).

| 프리셋 | 한국어 트리거(예) | 기본 씨앗 묶음 |
|--------|------------------|----------------|
| `solo_nude` | "야한 거", "벗은 그림" | `1girl, solo, nude, blush, looking at viewer` |
| `solo_masturbation` | "혼자 하는", "자위" | `1girl, solo, masturbation, fingering, spread legs, blush` |
| `missionary` | "기본 야한 장면", "정상위" | `1girl, 1boy, sex, vaginal, missionary, spread legs` |
| `from_behind` | "뒤에서", "후배위" | `1girl, 1boy, sex, doggystyle, from behind, ass` |
| `oral` | "구강", "입으로" | `1girl, 1boy, fellatio, oral, kneeling` |
| `lingerie_pinup` | "야한 속옷", "핀업" | `1girl, solo, lingerie, large breasts, seductive smile, looking at viewer` |

**선택 규칙(A 레이어)**: 입력이 §2 매핑으로 씨앗 ≥2개를 못 만들면 → 가장 가까운 프리셋 1개 채택 → 씨앗으로 사용. 어느 것도 안 맞으면 `solo_nude` 기본값.

---

## 4. A 레이어에서의 사용 (07 §2 연계)

이 문서는 A 레이어 NSFW 담당 모델(`qwen3:14b` 임상 분류 / 폴백 `abliterated`) 시스템 프롬프트에 **참조 사전**으로 주입된다(RAG 또는 직접 주입). 어느 모델이 담당하든 동일 사전을 참조.

1. 한국어 발화 수신 → §2 매핑·§3 프리셋 참조하여 **씨앗 태그만** 추출.
2. 출력은 07 §2 스키마(`positive_tags` = 씨앗). NSFW 등급은 `nsfw_level`에 기록.
3. 씨앗 → TIPO(B 합성) → allowlist(C 검증, §2-6 금지 시드 드롭) → 이미지 모델.
4. 검열 `qwen3:14b`가 거부한 등급만 A 레이어가 abliterated로 폴백(07 §1-A 원칙 2).

> 핵심: A 레이어는 **번역기**(한국어→씨앗)지 작가가 아니다. 풍부화는 TIPO, 안전은 allowlist가 맡는다.

---

## 5. 미해결 / 검증 필요 (가설 체크리스트)

- [ ] **H1**: TIPO가 적은 씨앗으로 NSFW 연관 태그를 충분히 확장하는가 (씨앗 3 vs 10 비교)
- [ ] **H2**: 매핑 주입이 abliterated의 한국어→태그 정확도를 실제로 올리는가 (allowlist 적중률)
- [ ] **H3**: 모호 입력에서 프리셋이 빈손을 막는가 (프리셋 유무 결과 차)
- [ ] **H4**: 표기 관례(공백/언더스코어·괄호)가 TIPO·체크포인트와 일치하는가 (Phase 1 실측)
- [ ] §2 매핑 용어가 실제 체크포인트(Illustrious/NoobAI)에서 의도대로 발현되는가
- [ ] 금지 시드 차단이 allowlist 단계에서 100% 동작하는가 (07 §1-A C 레이어)

## 관련 문서
- [07-프롬프트-및-파라미터-전략](07-프롬프트-및-파라미터-전략.md) (§1-A 레이어 분리, §2 스키마)
- [03-모델-선정](03-모델-선정.md) (abliterated·TIPO 배정)
