from __future__ import annotations

from typing import Optional


class ConfigMutationConflictError(Exception):
    """Error raised when a config mutation loses an optimistic snapshot race."""

    current_hash: Optional[str]
    retryable: bool

    def __init__(
        self,
        message: str,
        *,
        current_hash: Optional[str] = None,
        retryable: bool = True,
    ) -> None:
        super().__init__(message)
        self.current_hash = current_hash
        self.retryable = retryable

    def __reduce__(self):
        return (
            _unpickle_conflict,
            (str(self), self.current_hash, self.retryable),
        )


def _unpickle_conflict(message: str, current_hash, retryable: bool) -> "ConfigMutationConflictError":
    return ConfigMutationConflictError(message, current_hash=current_hash, retryable=retryable)
