# 피드백: abliterated 모델 성능 우려

> 발생: 2026-06-10, 오너가 huihui_ai/qwen3-abliterated:14b 직접 대화 테스트 후

## 무슨 문제인가
오너가 `huihui_ai/qwen3-abliterated:14b` pull 직후 직접 대화를 나눠봤는데 지능이 기대치보다 낮아보임.
Abliteration(거부 가중치 수술적 제거) 과정에서 일반 추론 능력도 함께 저하되는 알려진 트레이드오프.

## 왜 지금 당장 치명적이지 않은가
이 모델의 담당 역할은 **이미 파싱된 intent를 danbooru 태그 JSON으로 변환**하는 것.
복잡한 추론은 upstream의 `qwen3:14b`(검열, 고품질)가 담당하고 abliterated 모델은 변환만 함.
시스템 프롬프트 설계로 상당 부분 커버 가능한 작업.

## 앞으로 어떻게
- Phase 2 백엔드 파이프라인 구현 후 **실제 태그 생성 품질을 직접 테스트**해야 함
- 테스트 항목: JSON 스키마 준수율, hallucination 태그 빈도, 한국어 intent → 태그 변환 정확도
- **기준 미달 시 교체 후보**:
  - `dolphin3` (fine-tune 방식, 능력 보존 좋음 — 단 한국어 약함)
  - `huihui_ai/qwen3.5-abliterated:14b` (더 최신 베이스)
  - abliterated 포기 → explicit 태그를 rule-based로 append하는 방식으로 우회

## 교훈
abliterated 모델은 pull 전에 커뮤니티 실사용 후기를 추가로 확인하는 것이 좋음.
