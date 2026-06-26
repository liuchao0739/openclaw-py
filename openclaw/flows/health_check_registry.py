"""Health check registry stores doctor health checks by identifier.

Mirrors src/flows/health-check-registry.ts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, runtime_checkable


@runtime_checkable
class HealthCheck(Protocol):
    id: str
    kind: str


@dataclass
class HealthCheckImpl:
    """Concrete health check record."""

    id: str
    kind: str = "extension"
    run: Callable[..., Any] | None = None
    fix: Callable[..., Any] | None = None
    severity: str = "warning"
    title: str = ""
    description: str = ""


class HealthCheckRegistrationError(Exception):
    """Raised when two checks claim the same stable health-check id."""

    code: str = "OC_DOCTOR_DUPLICATE_CHECK"
    check_id: str

    def __init__(self, check_id: str) -> None:
        super().__init__(f"health check already registered: {check_id}")
        self.check_id = check_id


_REGISTRY: dict[str, Any] = {}


def register_health_check(check: Any) -> None:
    """Register one health check for doctor lint/fix execution."""
    check_id = getattr(check, "id", None) or (check.get("id") if isinstance(check, dict) else None)
    if check_id is None:
        raise ValueError("health check must have an id")
    if check_id in _REGISTRY:
        raise HealthCheckRegistrationError(check_id)
    _REGISTRY[check_id] = check


def list_health_checks() -> list[Any]:
    """Return registered checks in insertion order for deterministic doctor output."""
    return list(_REGISTRY.values())


def list_extension_health_checks_for_doctor(core_checks: list[Any]) -> list[Any]:
    """Return registered extension checks after rejecting reserved core doctor id claims."""
    core_ids = {getattr(c, "id", None) or (c.get("id") if isinstance(c, dict) else None) for c in core_checks}
    registered = list_health_checks()
    for check in registered:
        check_id = getattr(check, "id", None) or (check.get("id") if isinstance(check, dict) else None)
        if check_id and (check_id.startswith("core/doctor/") or check_id in core_ids):
            raise HealthCheckRegistrationError(check_id)
    return [
        c for c in registered
        if (getattr(c, "kind", None) or (c.get("kind") if isinstance(c, dict) else None)) != "core"
    ]


def get_health_check(check_id: str) -> Any | None:
    """Look up a registered health check by its stable id."""
    return _REGISTRY.get(check_id)


def clear_health_checks_for_test() -> None:
    """Clear the process-local registry for isolated tests."""
    _REGISTRY.clear()
