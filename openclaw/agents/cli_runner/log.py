"""Shared logging helpers for CLI backend diagnostics.

Mirrors src/agents/cli-runner/log.ts.
"""

from __future__ import annotations

import hashlib

CLI_BACKEND_LOG_OUTPUT_ENV = "OPENCLAW_CLI_BACKEND_LOG_OUTPUT"
LEGACY_CLAUDE_CLI_LOG_OUTPUT_ENV = "OPENCLAW_CLAUDE_CLI_LOG_OUTPUT"


def format_cli_backend_output_digest(text: str) -> str:
    """Return a compact byte/hash summary for CLI backend output."""
    out_bytes = len(text.encode("utf-8"))
    out_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    return f"outBytes={out_bytes} outHash={out_hash}"
