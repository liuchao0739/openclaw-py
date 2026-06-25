"""Attaches ProgramContext metadata to CLI program instances."""

from __future__ import annotations

from typing import Any

_PROGRAM_CONTEXT_KEY = "_openclaw_program_context"


def set_program_context(program: Any, ctx: Any) -> None:
    """Attach the current root ProgramContext to a program."""
    setattr(program, _PROGRAM_CONTEXT_KEY, ctx)


def get_program_context(program: Any) -> Any | None:
    """Read ProgramContext metadata from a program when available."""
    return getattr(program, _PROGRAM_CONTEXT_KEY, None)
