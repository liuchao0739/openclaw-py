from __future__ import annotations

from typing import Any


def build_install_security_scan(
    plugin_id: str,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "pluginId": plugin_id,
        "manifest": manifest or {},
        "issues": [],
        "riskLevel": "low",
    }


def run_install_security_scan(
    scan: dict[str, Any],
) -> dict[str, Any]:
    scan["completed"] = True
    return scan
