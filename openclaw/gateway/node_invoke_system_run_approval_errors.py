"""Shared system.run approval guard errors keep gateway/node responses

Mirrors src/gateway/node-invoke-system-run-approval-errors.ts.
"""

from __future__ import annotations

from typing import Any

def system_run_approval_guard_error(*args: Any, **kwargs: Any) -> Any: ...
def system_run_approval_required(*args: Any, **kwargs: Any) -> Any: ...
