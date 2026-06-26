"""Approval-policy command analysis normalizes shell and argv inputs into the
shared exec segment shape consumed by risk checks.

Mirrors src/infra/command-analysis/policy.ts. Self-contained port with basic
argv analysis and inline eval detection.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class ExecCommandSegment:
    """A single command segment (program or argument)."""

    text: str
    kind: str = "arg"  # "program" | "arg" | "flag" | "pipe" | "redirect"
    quoted: bool = False


@dataclass
class ExecCommandAnalysis:
    """Analysis result for an exec command."""

    ok: bool = True
    reason: str | None = None
    segments: list[ExecCommandSegment] = field(default_factory=list)
    program: str | None = None
    argv: list[str] = field(default_factory=list)


def _analyze_argv_command(
    argv: list[str],
    cwd: str | None = None,
    env: dict[str, str] | None = None,
) -> ExecCommandAnalysis:
    """Parse argv into command segments."""
    if not argv:
        return ExecCommandAnalysis(ok=False, reason="empty argv")
    segments: list[ExecCommandSegment] = []
    for i, arg in enumerate(argv):
        kind = "program" if i == 0 else ("flag" if arg.startswith("-") else "arg")
        segments.append(ExecCommandSegment(text=arg, kind=kind))
    return ExecCommandAnalysis(
        ok=True,
        segments=segments,
        program=argv[0],
        argv=list(argv),
    )


# Patterns that suggest inline evaluation (command substitution, eval, etc.)
_INLINE_EVAL_PATTERNS = [
    re.compile(r"\$\([^)]*\)"),  # $(...)
    re.compile(r"`[^`]*`"),  # `...`
    re.compile(r"\beval\b"),
    re.compile(r"\bexec\b"),
    re.compile(r"\bsource\b"),
    re.compile(r"\b\.\s"),
]


def detect_inline_eval_in_segments(
    segments: list[ExecCommandSegment],
) -> dict[str, Any]:
    """Detect inline evaluation patterns in command segments."""
    matches: list[str] = []
    for seg in segments:
        for pattern in _INLINE_EVAL_PATTERNS:
            if pattern.search(seg.text):
                matches.append(seg.text)
                break
    return {
        "detected": len(matches) > 0,
        "matches": matches,
    }


def detect_policy_inline_eval(
    segments: list[ExecCommandSegment],
) -> dict[str, Any]:
    """Detect inline eval in segments (alias for detect_inline_eval_in_segments)."""
    return detect_inline_eval_in_segments(segments)


def analyze_command_for_policy(
    params: dict[str, Any],
) -> dict[str, Any]:
    """Parse a shell or argv command into command segments for approval policy checks."""
    source = params.get("source", "argv")
    argv = params.get("argv", [])
    cwd = params.get("cwd")
    env = params.get("env")

    analysis = _analyze_argv_command(argv, cwd, env)
    if not analysis.ok:
        return {
            "ok": False,
            "source": source,
            "reason": analysis.reason,
            "analysis": analysis,
            "segments": [],
        }
    return {
        "ok": True,
        "source": source,
        "analysis": analysis,
        "segments": analysis.segments,
    }
