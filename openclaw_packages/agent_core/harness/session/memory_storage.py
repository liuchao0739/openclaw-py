from __future__ import annotations

import time
from typing import Any

from ..harness_types import SessionMetadata, SessionTreeEntry
from .storage_base import BaseSessionStorage
from .uuid import uuidv7


class InMemorySessionStorage(BaseSessionStorage):
    def __init__(self, options: dict[str, Any] | None = None) -> None:
        options = options or {}
        metadata = options.get("metadata")
        if metadata is None:
            from datetime import datetime, timezone
            metadata = SessionMetadata(
                id=uuidv7(),
                createdAt=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            )
        entries = options.get("entries") or []
        super().__init__(metadata, list(entries))

    async def set_leaf_id(self, leaf_id: str | None) -> None:
        self._record_entry(self._create_leaf_entry(leaf_id))

    async def append_entry(self, entry: SessionTreeEntry) -> None:
        self._record_entry(entry)
