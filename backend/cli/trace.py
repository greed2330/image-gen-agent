"""trace.py — Run one request through the pipeline and dump every stage's I/O.

Usage:
  python -m cli.trace "분홍 머리 트윈테일 소녀" [--dry-run] [--stage N]

  --dry-run   Stop before ComfyUI submission (stages ①–④ only).
              Use this when ComfyUI/GPU is not available.
  --stage N   Stop after stage N (1=intent, 2=route, 3=compile, 4=params).
              Implies dry-run for N<=4.

Example:
  python -m cli.trace "해변에서 웃고 있는 소녀" --dry-run
  python -m cli.trace "섹시한 포즈의 애니 캐릭터" --dry-run --stage 3
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.schemas import GenRequest


def _make_orchestrator(mock: bool = True):
    """Build an Orchestrator. mock=True injects stub clients for offline testing."""
    raise NotImplementedError


async def main(message: str, dry_run: bool, stage_limit: int | None) -> None:
    orchestrator = _make_orchestrator(mock=True)
    request = GenRequest(message=message, chat_id="cli-trace")

    result = await orchestrator.run(request, dry_run=dry_run, stage_limit=stage_limit)

    print("\n=== PIPELINE TRACE ===")
    print(result.trace.dump())

    if result.params:
        print("\n=== PARAMS ===")
        print(json.dumps(result.params.model_dump(), indent=2, ensure_ascii=False))

    if result.image_path:
        print(f"\n=== IMAGE ===\n{result.image_path}")

    if result.critique:
        print(f"\n=== CRITIQUE ===\npassed={result.critique.passed}  issues={result.critique.issues}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("message", help="Korean generation request")
    parser.add_argument("--dry-run", action="store_true", help="Stop before ComfyUI (stages ①–④)")
    parser.add_argument("--stage", type=int, default=None, metavar="N", help="Stop after stage N (1–4)")
    args = parser.parse_args()

    asyncio.run(main(args.message, dry_run=args.dry_run, stage_limit=args.stage))
