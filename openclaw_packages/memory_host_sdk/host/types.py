from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Union


MemorySource = str


@dataclass
class MemorySearchResult:
    path: str
    start_line: int
    end_line: int
    score: float
    snippet: str
    source: MemorySource
    vector_score: Optional[float] = None
    text_score: Optional[float] = None
    citation: Optional[str] = None


@dataclass
class MemoryEmbeddingProbeResult:
    ok: bool
    error: Optional[str] = None
    checked: Optional[bool] = None
    cached: Optional[bool] = None
    checked_at_ms: Optional[int] = None
    cache_expires_at_ms: Optional[int] = None


@dataclass
class MemorySyncProgressUpdate:
    completed: int
    total: int
    label: Optional[str] = None


@dataclass
class MemorySessionSyncTarget:
    session_id: str
    agent_id: Optional[str] = None
    session_key: Optional[str] = None


@dataclass
class MemorySyncParams:
    reason: Optional[str] = None
    force: Optional[bool] = None
    sessions: Optional[List[MemorySessionSyncTarget]] = None
    session_files: Optional[List[str]] = None
    progress: Optional[Callable] = None


@dataclass
class MemoryReadResult:
    text: str
    path: str
    truncated: Optional[bool] = None
    from_line: Optional[int] = None
    lines: Optional[int] = None
    next_from: Optional[int] = None


@dataclass
class MemoryProviderStatus:
    backend: str
    provider: str
    model: Optional[str] = None
    requested_provider: Optional[str] = None
    files: Optional[int] = None
    chunks: Optional[int] = None
    dirty: Optional[bool] = None
    workspace_dir: Optional[str] = None
    db_path: Optional[str] = None
    extra_paths: Optional[List[str]] = None
    sources: Optional[List[MemorySource]] = None
    source_counts: Optional[List[dict]] = None
    cache: Optional[dict] = None
    fts: Optional[dict] = None
    fallback: Optional[dict] = None
    vector: Optional[dict] = None
    batch: Optional[dict] = None
    custom: Optional[dict] = None


class MemorySearchManager:
    async def search(self, query: str, opts: Optional[dict] = None) -> List[MemorySearchResult]:
        raise NotImplementedError

    async def read_file(self, params: dict) -> MemoryReadResult:
        raise NotImplementedError

    def status(self) -> MemoryProviderStatus:
        raise NotImplementedError

    async def sync(self, params: Optional[MemorySyncParams] = None) -> None:
        raise NotImplementedError

    def get_cached_embedding_availability(self) -> Optional[MemoryEmbeddingProbeResult]:
        raise NotImplementedError

    async def probe_embedding_availability(self) -> MemoryEmbeddingProbeResult:
        raise NotImplementedError

    async def probe_vector_availability(self) -> bool:
        raise NotImplementedError

    async def probe_vector_store_availability(self) -> Optional[bool]:
        raise NotImplementedError

    async def close(self) -> None:
        pass
