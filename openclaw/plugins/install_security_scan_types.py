from __future__ import annotations

from typing import Any


def build_install_security_scan_types() -> dict[str, Any]:
    return {
        "riskLevels": ["low", "medium", "high", "critical"],
        "scanTypes": ["dependency", "code", "config"],
    }


def resolve_risk_level(score: float) -> str:
    if score >= 0.8:
        return "critical"
    if score >= 0.6:
        return "high"
    if score >= 0.3:
        return "medium"
    return "low"
