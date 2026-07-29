from __future__ import annotations


def format_config_recovery_hint(error: Exception) -> str:
    return f"Config recovery hint: {error}"


def has_config_recovery_hint(error: Exception) -> bool:
    return "config" in str(error).lower()
