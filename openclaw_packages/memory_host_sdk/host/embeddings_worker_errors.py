from __future__ import annotations

from typing import Any, Dict, List, Optional


LOCAL_EMBEDDING_WORKER_ERROR_CODES = {
    "exited": "local-embedding-worker-exited",
    "processError": "local-embedding-worker-process-error",
    "ipcError": "local-embedding-worker-ipc-error",
}


class LocalEmbeddingWorkerError(Exception):
    def __init__(self, message: str, code: Optional[str] = None, reason: Optional[str] = None):
        super().__init__(message)
        self.code = code
        self.reason = reason


def create_local_embedding_worker_failure_error(
    message: str,
    code: Optional[str] = None,
    reason: Optional[str] = None,
    exit_code: Optional[int] = None,
    signal: Optional[str] = None,
    cause: Optional[Exception] = None,
) -> LocalEmbeddingWorkerError:
    error = LocalEmbeddingWorkerError(message, code, reason)
    error.exit_code = exit_code
    error.signal = signal
    error.__cause__ = cause
    return error
