"""chat.py — Interactive REPL for testing the pipeline with memory.

Usage:
  python -m cli.chat [--chat-id ROOM] [--dry-run]

  --chat-id   Chat room ID (default: "cli-test"). Memories persist across runs.
  --dry-run   Skip ComfyUI generation — test intent/compile/params only.

Commands inside REPL:
  /memory     Print all memories stored for this chat room
  /trace      Toggle trace output on/off (default: off)
  /quit       Exit

Purpose: Verify that mem0 stores preferences across turns and that the pipeline
picks up context ("같은 스타일로 다시", "배경만 바꿔줘") correctly.
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def _make_orchestrator(mock: bool = True):
    raise NotImplementedError


def _make_memory_service():
    raise NotImplementedError


async def repl(chat_id: str, dry_run: bool) -> None:
    orchestrator = _make_orchestrator(mock=True)
    memory = _make_memory_service()
    show_trace = False

    print(f"chat room: {chat_id}  (dry_run={dry_run})")
    print("Commands: /memory  /trace  /quit\n")

    from app.models.schemas import GenRequest

    while True:
        try:
            msg = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not msg:
            continue
        if msg == "/quit":
            break
        if msg == "/memory":
            entries = await memory.get_all(chat_id)
            print(f"[memory] {len(entries)} entries")
            for e in entries:
                print(" ", e)
            continue
        if msg == "/trace":
            show_trace = not show_trace
            print(f"[trace] {'on' if show_trace else 'off'}")
            continue

        request = GenRequest(message=msg, chat_id=chat_id)
        result = await orchestrator.run(request, dry_run=dry_run)

        if show_trace:
            print(result.trace.dump())

        if result.image_path:
            print(f"[image] {result.image_path}")
        elif result.params:
            print(f"[dry-run] steps={result.params.steps} cfg={result.params.cfg}")
        else:
            print("[result] pipeline ran (no image yet)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--chat-id", default="cli-test")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    asyncio.run(repl(args.chat_id, args.dry_run))
