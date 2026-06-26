"""Raised when a config write loses an optimistic snapshot race."""


class ConfigMutationConflictError(Exception):
    """Error raised when a config mutation loses an optimistic snapshot race."""

    current_hash: str | None
    retryable: bool

    def __init__(
        self,
        message: str,
        *,
        current_hash: str | None = None,
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
