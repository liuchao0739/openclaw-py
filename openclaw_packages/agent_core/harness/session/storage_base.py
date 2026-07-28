from __future__ import annotations

import abc
import time
from typing import Any

from ..harness_types import (
    LabelEntry,
    LeafEntry,
    SessionError,
    SessionMetadata,
    SessionTreeEntry,
)
from .uuid import uuidv7


def _update_label_cache(labels_by_id: dict[str, str], entry: SessionTreeEntry) -> None:
    if entry.type != "label":
        return
    label = getattr(entry, "label", None)
    if label:
        labels_by_id[entry.targetId] = label
    else:
        labels_by_id.pop(entry.targetId, None)


def _build_labels_by_id(entries: list[SessionTreeEntry]) -> dict[str, str]:
    labels_by_id: dict[str, str] = {}
    for entry in entries:
        _update_label_cache(labels_by_id, entry)
    return labels_by_id


def _is_side_append_entry(entry: SessionTreeEntry) -> bool:
    return getattr(entry, "appendMode", None) == "side"


def _generate_entry_id(by_id: dict[str, SessionTreeEntry]) -> str:
    for _ in range(100):
        entry_id = uuidv7()[:8]
        if entry_id not in by_id:
            return entry_id
    return uuidv7()


def leaf_id_update_after_entry(entry: SessionTreeEntry) -> str | None:
    if entry.type != "leaf" and _is_side_append_entry(entry):
        return None
    if entry.type == "leaf":
        return entry.targetId
    if entry.type in (
        "message",
        "thinking_level_change",
        "model_change",
        "compaction",
        "branch_summary",
        "custom",
        "custom_message",
        "label",
        "session_info",
    ):
        return entry.id
    return None


def append_parent_id_after_entry(entry: SessionTreeEntry) -> str | None:
    if entry.type == "leaf":
        if entry.appendParentId is None:
            return entry.targetId
        return entry.appendParentId
    return entry.id


def _resolve_leaf_id(entries: list[SessionTreeEntry]) -> str | None:
    leaf_id: str | None = None
    for entry in entries:
        update = leaf_id_update_after_entry(entry)
        if update is not None:
            leaf_id = update
    return leaf_id


def _resolve_append_parent_id(entries: list[SessionTreeEntry]) -> str | None:
    append_parent_id: str | None = None
    for entry in entries:
        append_parent_id = append_parent_id_after_entry(entry)
    return append_parent_id


def _build_logical_parents_by_id(
    entries: list[SessionTreeEntry],
) -> dict[str, str | None]:
    logical_parents_by_id: dict[str, str | None] = {}
    leaf_id: str | None = None
    append_parent_id: str | None = None
    for entry in entries:
        leaf_update = leaf_id_update_after_entry(entry)
        if (
            leaf_update == entry.id
            and not _is_side_append_entry(entry)
            and entry.parentId == append_parent_id
            and leaf_id != append_parent_id
        ):
            logical_parents_by_id[entry.id] = leaf_id
        if leaf_update is not None:
            leaf_id = leaf_update
        append_parent_id = append_parent_id_after_entry(entry)
    return logical_parents_by_id


class BaseSessionStorage(abc.ABC):
    def __init__(
        self,
        metadata: SessionMetadata,
        entries: list[SessionTreeEntry],
        leaf_id: str | None | None = None,
        append_parent_id: str | None | None = None,
    ) -> None:
        self._metadata = metadata
        self._entries: list[SessionTreeEntry] = list(entries)
        self._by_id: dict[str, SessionTreeEntry] = {
            entry.id: entry for entry in self._entries
        }
        self._labels_by_id: dict[str, str] = _build_labels_by_id(self._entries)
        self._logical_parents_by_id: dict[str, str | None] = _build_logical_parents_by_id(
            self._entries
        )
        self._leaf_id: str | None = (
            leaf_id if leaf_id is not None else _resolve_leaf_id(self._entries)
        )
        self._append_parent_id: str | None = (
            append_parent_id
            if append_parent_id is not None
            else _resolve_append_parent_id(self._entries)
        )
        if self._leaf_id is not None and self._leaf_id not in self._by_id:
            raise SessionError("invalid_session", f"Entry {self._leaf_id} not found")
        if (
            self._append_parent_id is not None
            and self._append_parent_id not in self._by_id
        ):
            raise SessionError(
                "invalid_session",
                f"Append parent {self._append_parent_id} not found",
            )

    async def get_metadata(self) -> SessionMetadata:
        return self._metadata

    async def get_leaf_id(self) -> str | None:
        if self._leaf_id is not None and self._leaf_id not in self._by_id:
            raise SessionError(
                "invalid_session", f"Entry {self._leaf_id} not found"
            )
        return self._leaf_id

    async def get_append_parent_id(self) -> str | None:
        if (
            self._append_parent_id is not None
            and self._append_parent_id not in self._by_id
        ):
            raise SessionError(
                "invalid_session",
                f"Append parent {self._append_parent_id} not found",
            )
        return self._append_parent_id

    def _create_leaf_entry(self, leaf_id: str | None) -> LeafEntry:
        if leaf_id is not None and leaf_id not in self._by_id:
            raise SessionError("not_found", f"Entry {leaf_id} not found")
        return LeafEntry(
            type="leaf",
            id=_generate_entry_id(self._by_id),
            parentId=self._append_parent_id,
            timestamp=_now_iso(),
            targetId=leaf_id,
        )

    async def create_entry_id(self) -> str:
        return _generate_entry_id(self._by_id)

    def _validate_entry_for_append(self, entry: SessionTreeEntry) -> None:
        leaf_id = leaf_id_update_after_entry(entry)
        leaf_is_new_entry = entry.type != "leaf" and leaf_id == entry.id
        if (
            leaf_id is not None
            and not leaf_is_new_entry
            and leaf_id not in self._by_id
        ):
            raise SessionError("not_found", f"Entry {leaf_id} not found")

        append_parent_id = append_parent_id_after_entry(entry)
        append_parent_is_new_entry = (
            entry.type != "leaf" and append_parent_id == entry.id
        )
        if (
            append_parent_id is not None
            and not append_parent_is_new_entry
            and append_parent_id not in self._by_id
        ):
            raise SessionError(
                "not_found",
                f"Append parent {append_parent_id} not found",
            )

    def _record_entry(self, entry: SessionTreeEntry) -> None:
        self._validate_entry_for_append(entry)
        leaf_id = leaf_id_update_after_entry(entry)
        if (
            leaf_id == entry.id
            and not _is_side_append_entry(entry)
            and entry.parentId == self._append_parent_id
            and self._leaf_id != self._append_parent_id
        ):
            self._logical_parents_by_id[entry.id] = self._leaf_id
        self._entries.append(entry)
        self._by_id[entry.id] = entry
        _update_label_cache(self._labels_by_id, entry)
        if leaf_id is not None:
            self._leaf_id = leaf_id
        self._append_parent_id = append_parent_id_after_entry(entry)

    async def get_entry(self, entry_id: str) -> SessionTreeEntry | None:
        return self._by_id.get(entry_id)

    async def find_entries(self, entry_type: str) -> list[SessionTreeEntry]:
        return [entry for entry in self._entries if entry.type == entry_type]

    async def get_label(self, entry_id: str) -> str | None:
        return self._labels_by_id.get(entry_id)

    async def get_path_to_root(self, leaf_id: str | None) -> list[SessionTreeEntry]:
        if leaf_id is None:
            return []
        path: list[SessionTreeEntry] = []
        current = self._by_id.get(leaf_id)
        if current is None:
            raise SessionError("not_found", f"Entry {leaf_id} not found")
        seen: set[str] = set()
        while current is not None:
            if current.id in seen:
                raise SessionError(
                    "invalid_session",
                    f"Cycle found at entry {current.id}",
                )
            seen.add(current.id)
            if current.type != "leaf":
                path.insert(0, current)
            if current.type == "leaf":
                parent_id = current.targetId
            elif current.id in self._logical_parents_by_id:
                parent_id = self._logical_parents_by_id[current.id]
            else:
                parent_id = current.parentId
            if not parent_id:
                break
            parent = self._by_id.get(parent_id)
            if parent is None:
                raise SessionError(
                    "invalid_session",
                    f"Entry {parent_id} not found",
                )
            current = parent
        return path

    async def get_entries(self) -> list[SessionTreeEntry]:
        return list(self._entries)

    @abc.abstractmethod
    async def set_leaf_id(self, leaf_id: str | None) -> None: ...

    @abc.abstractmethod
    async def append_entry(self, entry: SessionTreeEntry) -> None: ...


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
