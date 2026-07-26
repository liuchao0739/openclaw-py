#!/usr/bin/env python3
"""Print the next pending migration task from the TypeScript repo's progress file.

Phase-3 entries only carry a `source_id` pointing back at the phase-2 task that
holds the actual source/target paths, so those get resolved here.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

DEFAULT_TS_REPO = "/Users/liuchao/openclaw-ts"


def ts_repo() -> Path:
    return Path(os.environ.get("OPENCLAW_TS_REPO", DEFAULT_TS_REPO))


def progress_file(phase: str) -> Path:
    name = "progress.json" if phase == "mvp" else f"progress-phase{phase}.json"
    return ts_repo() / "migration" / name


def load_tasks(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["tasks"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", default="3")
    parser.add_argument("--count", type=int, default=1)
    args = parser.parse_args()

    path = progress_file(args.phase)
    if not path.is_file():
        print(f"missing {path}", file=sys.stderr)
        return 1

    tasks = load_tasks(path)
    pending = [t for t in tasks if t.get("status") != "done"]
    done = len(tasks) - len(pending)
    print(f"progress: {done}/{len(tasks)} done, {len(pending)} pending\n")
    if not pending:
        print("MIGRATION_COMPLETE")
        return 0

    fallback: dict[str, dict] = {}
    if args.phase == "3":
        phase2 = progress_file("2")
        if phase2.is_file():
            fallback = {t["id"]: t for t in load_tasks(phase2)}

    for task in pending[: args.count]:
        detail = fallback.get(task.get("source_id", ""), {})
        print(task["id"], task["title"])
        print("  source:", task.get("source_paths") or detail.get("source_paths"))
        print("  target:", task.get("target_paths") or detail.get("target_paths"))
        print("  files:", task.get("file_count") or detail.get("file_count"))
        print("  acceptance:", task.get("acceptance") or detail.get("acceptance"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
