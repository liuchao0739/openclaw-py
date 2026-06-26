"""ACP runtime package — errors, availability, registry.

Mirrors src/acp/runtime/.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping


class AcpRuntimeError(Exception):
    """Base ACP runtime error with secret redaction support."""

    code: str = "ACP_RUNTIME_ERROR"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code:
            self.code = code


class AcpSessionNotFoundError(AcpRuntimeError):
    code = "ACP_SESSION_NOT_FOUND"

    def __init__(self, session_key: str) -> None:
        super().__init__(f"ACP session not found: {session_key}")


class AcpBackendUnavailableError(AcpRuntimeError):
    code = "ACP_BACKEND_UNAVAILABLE"

    def __init__(self, backend_id: str | None = None) -> None:
        super().__init__(f"ACP backend unavailable: {backend_id or 'default'}")


# --- Redaction ---

_redactor: Callable[[str], str] | None = None


def configure_acp_error_redactor(redactor: Callable[[str], str]) -> None:
    """Configure a redactor for sensitive text in ACP error messages."""
    global _redactor
    _redactor = redactor


def redact_sensitive_text(text: str) -> str:
    """Redact sensitive text using the configured redactor."""
    if _redactor:
        return _redactor(text)
    return text


# --- Registry ---

_acp_backends: dict[str, dict[str, Any]] = {}


def register_acp_runtime_backend(
    backend_id: str,
    backend: dict[str, Any],
) -> None:
    """Register an ACP runtime backend."""
    _acp_backends[backend_id] = backend


def get_acp_runtime_backend(backend_id: str | None = None) -> dict[str, Any] | None:
    """Return the ACP runtime backend for the given id, or None."""
    if not backend_id:
        # Return first registered backend
        if _acp_backends:
            return next(iter(_acp_backends.values()))
        return None
    return _acp_backends.get(backend_id)


def require_acp_runtime_backend(backend_id: str | None = None) -> dict[str, Any]:
    """Return the ACP runtime backend or raise."""
    backend = get_acp_runtime_backend(backend_id)
    if backend is None:
        raise AcpBackendUnavailableError(backend_id)
    return backend


def reset_acp_backends_for_tests() -> None:
    """Clear all registered backends."""
    _acp_backends.clear()


# --- Availability ---

def is_acp_enabled_by_policy(config: Mapping[str, Any] | None) -> bool:
    """Check if ACP is enabled by policy."""
    if not config:
        return True
    acp = config.get("acp") if isinstance(config, Mapping) else None
    if isinstance(acp, Mapping):
        return acp.get("enabled", True) is not False
    return True


def is_acp_runtime_spawn_available(
    config: Mapping[str, Any] | None = None,
    sandboxed: bool | None = None,
    backend_id: str | None = None,
) -> bool:
    """Return whether ACP runtime spawning is allowed and the backend is healthy."""
    if sandboxed is True:
        return False
    if config and not is_acp_enabled_by_policy(config):
        return False
    resolved_backend_id = backend_id
    if not resolved_backend_id and isinstance(config, Mapping):
        acp_cfg = config.get("acp")
        if isinstance(acp_cfg, Mapping):
            resolved_backend_id = acp_cfg.get("backend")
    backend = get_acp_runtime_backend(resolved_backend_id)
    if backend is None:
        return False
    healthy_fn = backend.get("healthy")
    if not callable(healthy_fn):
        return True
    try:
        return bool(healthy_fn())
    except Exception:
        return False
