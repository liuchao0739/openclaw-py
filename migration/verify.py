#!/usr/bin/env python3
"""Verify a single migration task against its TypeScript source.

This is the acceptance gate for the loop. A task only counts as done when the
exported API of the source module actually exists in the Python target, which
is what stops the loop from satisfying itself with invented stubs.

Usage:
    python migration/verify.py P2-0217
    python migration/verify.py P2-0217 --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ts_symbols import match_symbols, read_module, read_python_symbols, ts_repo

PY_ROOT = Path(__file__).resolve().parent.parent
PLAN = PY_ROOT / "migration" / "plan.json"

PASS_THRESHOLD = 0.85


def load_plan(path: Path = PLAN) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_task(plan: list[dict], task_id: str) -> dict | None:
    return next((task for task in plan if task["id"] == task_id), None)


def verify_task(task: dict) -> dict:
    """Compare a task's TypeScript exports against its Python target."""
    source = ts_repo() / task["source"]
    target = PY_ROOT / task["target"]
    facts = read_module(source)
    ported, missing = match_symbols(facts.api, read_python_symbols(target))

    total = len(facts.api)
    coverage = 1.0 if total == 0 else len(ported) / total
    return {
        "id": task["id"],
        "source": task["source"],
        "target": task["target"],
        "target_exists": target.exists(),
        "expected": total,
        "ported": len(ported),
        "coverage": round(coverage, 4),
        "passed": target.exists() and coverage >= PASS_THRESHOLD,
        "missing_symbols": sorted(missing),
        "expected_symbols": sorted(facts.api),
        "ts_source_lines": facts.source_lines,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("task_id")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--plan", type=Path, default=PLAN)
    args = parser.parse_args()

    plan = load_plan(args.plan)
    task = find_task(plan, args.task_id)
    if task is None:
        print(f"unknown task {args.task_id}", file=sys.stderr)
        return 2

    result = verify_task(task)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"{status} {result['id']} {result['source']}")
        print(
            f"  exported api: {result['ported']}/{result['expected']} "
            f"({round(result['coverage'] * 100)}%)"
        )
        if result["missing_symbols"]:
            shown = result["missing_symbols"][:30]
            print(f"  missing: {', '.join(shown)}")
            if len(result["missing_symbols"]) > len(shown):
                print(f"  ... and {len(result['missing_symbols']) - len(shown)} more")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
