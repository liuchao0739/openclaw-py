#!/usr/bin/env python3
"""Print the next pending migration tasks from the dependency-ordered plan.

Regenerate the plan with:
    python migration/audit.py --json migration/audit.json
    python migration/depgraph.py --json migration/plan.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PLAN = Path(__file__).resolve().parent.parent / "migration" / "plan.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--plan", type=Path, default=PLAN)
    args = parser.parse_args()

    if not args.plan.is_file():
        print(f"missing {args.plan}; run migration/depgraph.py first", file=sys.stderr)
        return 1

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    pending = [task for task in plan if task.get("status") != "done"]
    done = len(plan) - len(pending)
    remaining_lines = sum(task["ts_source_lines"] for task in pending)
    print(f"progress: {done}/{len(plan)} modules ported, {len(pending)} pending")
    print(f"remaining: {remaining_lines:,} TypeScript source lines\n")

    if not pending:
        print("MIGRATION_COMPLETE")
        return 0

    for task in pending[: args.count]:
        print(f"[{task['order']}] {task['id']} {task['title']}")
        print(f"  source: {task['source']}  ->  target: {task['target']}")
        print(
            f"  grade: {task['grade']}  files: {task['file_count']}  "
            f"ts lines: {task['ts_source_lines']}  exported api: {task['ts_api_count']}"
        )
        if task["cycle_size"] > 1:
            print(
                f"  note: inside a {task['cycle_size']}-task import cycle; "
                f"boundary stubs are unavoidable here"
            )
        deps = task["depends_on"]
        if deps:
            print(f"  depends on: {', '.join(deps[:8])}{' ...' if len(deps) > 8 else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
