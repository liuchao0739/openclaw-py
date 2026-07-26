#!/usr/bin/env python3
"""Audit how much of each TypeScript module actually exists in the Python port.

Phase-2 marked 231 modules "done" while many targets hold invented APIs with no
counterpart in the source. This grades every task by how many exported symbols
have a same-named Python definition, so the plan can be rebuilt from reality.

Usage:
    python migration/audit.py [--json migration/audit.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ts_symbols import (
    match_symbols,
    python_line_count,
    read_module,
    read_python_symbols,
    ts_repo,
)

PY_ROOT = Path(__file__).resolve().parent.parent

# Below this share of ported symbols a target is treated as not really migrated.
STUB_THRESHOLD = 0.25
PARTIAL_THRESHOLD = 0.85


def grade(ported: int, total: int, target_exists: bool) -> str:
    if not target_exists:
        return "missing"
    if total == 0:
        return "trivial"
    ratio = ported / total
    if ratio < STUB_THRESHOLD:
        return "stub"
    if ratio < PARTIAL_THRESHOLD:
        return "partial"
    return "ported"


def load_phase2_tasks() -> list[dict]:
    path = ts_repo() / "migration" / "progress-phase2.json"
    return json.loads(path.read_text(encoding="utf-8"))["tasks"]


def audit() -> list[dict]:
    repo = ts_repo()
    results: list[dict] = []

    for task in load_phase2_tasks():
        source_paths = task.get("source_paths") or []
        target_paths = task.get("target_paths") or []
        if not source_paths or not target_paths:
            continue

        source = repo / source_paths[0]
        target = PY_ROOT / target_paths[0]
        facts = read_module(source)
        py_names = read_python_symbols(target)
        ported, missing = match_symbols(facts.api, py_names)

        results.append(
            {
                "id": task["id"],
                "title": task.get("title", ""),
                "source": source_paths[0],
                "target": target_paths[0],
                "source_exists": source.is_dir(),
                "target_exists": target.exists(),
                "ts_api_count": len(facts.api),
                "ported_count": len(ported),
                "grade": grade(len(ported), len(facts.api), target.exists()),
                "ts_source_lines": facts.source_lines,
                "ts_test_lines": facts.test_lines,
                "py_lines": python_line_count(target),
                "missing_symbols": sorted(missing)[:40],
            }
        )

    return results


def summarize(results: list[dict]) -> None:
    buckets: dict[str, list[dict]] = {}
    for row in results:
        buckets.setdefault(row["grade"], []).append(row)

    total_api = sum(r["ts_api_count"] for r in results)
    total_ported = sum(r["ported_count"] for r in results)

    print(f"audited {len(results)} phase-2 modules against {ts_repo()}\n")
    print(f"{'grade':10} {'modules':>8} {'ts_api':>8} {'ported':>8} {'ts_lines':>9}")
    for name in ("ported", "partial", "stub", "missing", "trivial"):
        rows = buckets.get(name, [])
        if not rows:
            continue
        print(
            f"{name:10} {len(rows):8} {sum(r['ts_api_count'] for r in rows):8} "
            f"{sum(r['ported_count'] for r in rows):8} "
            f"{sum(r['ts_source_lines'] for r in rows):9}"
        )
    pct = round(100 * total_ported / total_api) if total_api else 0
    print(f"\noverall: {total_ported}/{total_api} exported symbols present ({pct}%)")

    remaining = [r for r in results if r["grade"] in ("stub", "missing", "partial")]
    lines = sum(r["ts_source_lines"] for r in remaining)
    print(f"remaining work: {len(remaining)} modules, ~{lines:,} TypeScript source lines")

    worst = sorted(remaining, key=lambda r: -r["ts_source_lines"])[:15]
    print(f"\nlargest unported modules:\n{'module':52} {'grade':9} {'lines':>7} {'api':>5}")
    for row in worst:
        print(
            f"{row['source'][:52]:52} {row['grade']:9} "
            f"{row['ts_source_lines']:7} {row['ts_api_count']:5}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args()

    if not ts_repo().is_dir():
        print(f"missing TypeScript repo at {ts_repo()}", file=sys.stderr)
        return 1

    results = audit()
    summarize(results)
    if args.json:
        args.json.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
