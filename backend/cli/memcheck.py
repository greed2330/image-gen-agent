"""memcheck.py — Multi-turn memory verification scenario.

Runs a scripted conversation and checks that:
1. User preferences stated in turn 1 are retrieved in turn 3.
2. Style/character choices are remembered across turns.
3. mem0 search returns the right memories for a follow-up query.

Usage:
  python -m cli.memcheck

Expected output: PASS/FAIL for each check with retrieved memory content.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

SCENARIO = [
    "분홍 머리 트윈테일 소녀를 부드러운 셀화 스타일로 그려줘",
    "방금 그 스타일로 바다 배경으로 다시 그려줘",
    "이 캐릭터 기억해? 어떤 스타일이었어?",  # memory retrieval check
]


def _make_memory_service():
    raise NotImplementedError


async def run_scenario() -> None:
    memory = _make_memory_service()
    chat_id = "memcheck-test"

    print("=== memory scenario ===\n")
    for i, msg in enumerate(SCENARIO, 1):
        print(f"turn {i}: {msg}")
        # In Phase 2: run through orchestrator and record memory here
        # For now: stub
        raise NotImplementedError

    print("\n=== checks ===")
    results = await memory.search(chat_id, "스타일", top_k=3)
    print(f"memory search 'スタイル': {results}")
    print("PASS" if results else "FAIL — no memories found")


if __name__ == "__main__":
    asyncio.run(run_scenario())
