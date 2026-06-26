"""Crestodian audit helpers append JSONL records for approved local-state changes.

Mirrors src/crestodian/audit.ts:
- ``resolve_crestodian_audit_path`` builds ``<stateDir>/audit/crestodian.jsonl``.
- ``append_crestodian_audit_entry`` appends a timestamped JSONL line, creating
  parent directories, and rejects symlinked parents so approval records cannot
  be redirected silently.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, TypedDict


class CrestodianAuditEntry(TypedDict, total=False):
    timestamp: str
    operation: str
    summary: str
    configPath: str
    configHashBefore: str | None
    configHashAfter: str | None
    details: dict[str, Any]


def resolve_crestodian_audit_path(
    env: Mapping[str, str] | None = None,
    state_dir: str | None = None,
) -> str:
    """Resolve the JSONL audit path for Crestodian persistent operations."""
    if state_dir is None:
        state_dir = _default_state_dir(env)
    return str(Path(state_dir) / "audit" / "crestodian.jsonl")


async def append_crestodian_audit_entry(
    entry: Mapping[str, Any],
    *,
    env: Mapping[str, str] | None = None,
    audit_path: str | None = None,
) -> str:
    """Append one Crestodian audit entry and return the file path written."""
    if audit_path is None:
        audit_path = resolve_crestodian_audit_path(env)
    p = Path(audit_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    _ensure_no_symlink_parent(p)
    line = json.dumps(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **entry,
        },
        ensure_ascii=False,
    )
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    return audit_path


def _default_state_dir(env: Mapping[str] | None) -> str:
    """Best-effort default state dir from env, mirroring config/paths logic."""
    env = env or os.environ
    return env.get("OPENCLAW_STATE_DIR") or str(Path.home() / ".openclaw")


def _ensure_no_symlink_parent(path: Path) -> None:
    """Reject symlinked parents so approval records cannot be redirected silently."""
    current = path.parent.resolve()
    # Walk up the resolved path checking that no ancestor is a symlink.
    check = path.parent
    seen: set[Path] = set()
    while check != check.parent:
        if check in seen:
            break
        seen.add(check)
        if check.is_symlink():
            raise OSError(f"Symlinked parent rejected for audit path: {check}")
        check = check.parent
