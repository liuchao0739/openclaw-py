#!/usr/bin/env python3
"""Print the next pending P2 task from openclaw/migration/progress-phase2.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROGRESS = Path("/Users/liuchao/openclaw/migration/progress-phase2.json")


def main() -> int:
    if not PROGRESS.is_file():
        print(f"missing {PROGRESS}", file=sys.stderr)
        return 1
    data = json.loads(PROGRESS.read_text())
    pending = [t for t in data["tasks"] if t.get("status") != "done"]
    if not pending:
        print("MIGRATION_COMPLETE")
        return 0
    t = pending[0]
    print(t["id"], t["title"])
    print("source:", t["source_paths"])
    print("target:", t["target_paths"])
    print("files:", t.get("file_count"))
    print("acceptance:", t.get("acceptance"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())