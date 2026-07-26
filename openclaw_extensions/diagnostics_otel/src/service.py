"""Diagnostics Otel plugin module implements service behavior."""

from __future__ import annotations

import importlib
from typing import Any


def create_diagnostics_otel_service() -> Any:
    """Create the diagnostics-otel OpenClaw plugin service."""
    service_runtime = importlib.import_module(
        "openclaw_extensions.diagnostics_otel.src.service_runtime"
    )
    return service_runtime.create_diagnostics_otel_service()
