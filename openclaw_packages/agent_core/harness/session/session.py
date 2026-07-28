from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ...agent_types import AgentMessage
from ..harness_types import (
    BranchSummaryEntry,
    CompactionEntry,
    CustomEntry,
    CustomMessageEntry,
    LabelEntry,
    MessageEntry,
    ModelChangeEntry,
    SessionContext,
    SessionError,
    SessionMetadata,
    SessionStorage,
    SessionTreeEntry,
    SessionInfoEntry,
    ThinkingLevelChangeEntry,
)


def _lazy_messages():
    from ..messages import (
        as_agent_message,
        create_branch_summary_message,
        create_compaction_summary_message,
        create_custom_message,
    )
    return as_agent_message, create_branch_summary_message, create_compaction_summary_message, create_custom_message


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_session_context(path_entries: list[SessionTreeEntry]) -> SessionContext:
    as_agent_message, create_branch_summary_message, create_compaction_summary_message, create_custom_message = _lazy_messages()
    thinking_level = "off"
    model: dict[str, str] | None = None
    compaction: CompactionEntry | None = None

    for entry in path_entries:
        if entry.type == "thinking_level_change":
            thinking_level = entry.thinkingLevel
        elif entry.type == "model_change":
            model = {"provider": entry.provider, "modelId": entry.modelId}
        elif entry.type == "message" and entry.message.get("role") == "assistant":
            model = {
                "provider": entry.message.get("provider", ""),
                "modelId": entry.message.get("model", ""),
            }
        elif entry.type == "compaction":
            compaction = entry

    messages: list[AgentMessage] = []

    def _append_message(entry: SessionTreeEntry) -> None:
        if entry.type == "message":
            messages.append(entry.message)
        elif entry.type == "custom_message":
            messages.append(
                as_agent_message(
                    create_custom_message(
                        entry.customType,
                        entry.content,
                        entry.display,
                        entry.details,
                        entry.timestamp,
                    )
                )
            )
        elif entry.type == "branch_summary" and entry.summary:
            messages.append(
                as_agent_message(
                    create_branch_summary_message(
                        entry.summary,
                        entry.fromId,
                        entry.timestamp,
                    )
                )
            )

    if compaction is not None:
        messages.append(
            as_agent_message(
                create_compaction_summary_message(
                    compaction.summary,
                    compaction.tokensBefore,
                    compaction.timestamp,
                )
            )
        )
        compaction_idx = next(
            (
                i
                for i, e in enumerate(path_entries)
                if e.type == "compaction" and e.id == compaction.id
            ),
            -1,
        )
        found_first_kept = False
        for i in range(compaction_idx):
            entry = path_entries[i]
            if entry.id == compaction.firstKeptEntryId:
                found_first_kept = True
            if found_first_kept:
                _append_message(entry)
        for i in range(compaction_idx + 1, len(path_entries)):
            _append_message(path_entries[i])
    else:
        for entry in path_entries:
            _append_message(entry)

    return SessionContext(
        messages=messages,
        thinkingLevel=thinking_level,
        model=model,
    )


class Session:
    def __init__(self, storage: SessionStorage) -> None:
        self._storage = storage

    async def get_metadata(self) -> SessionMetadata:
        return await self._storage.getMetadata()

    def get_storage(self) -> SessionStorage:
        return self._storage

    async def get_leaf_id(self) -> str | None:
        return await self._storage.getLeafId()

    async def _get_append_parent_id(self) -> str | None:
        if hasattr(self._storage, "getAppendParentId"):
            return await self._storage.getAppendParentId()
        return await self._storage.getLeafId()

    async def get_entry(self, entry_id: str) -> SessionTreeEntry | None:
        return await self._storage.getEntry(entry_id)

    async def get_entries(self) -> list[SessionTreeEntry]:
        return await self._storage.getEntries()

    async def get_branch(self, from_id: str | None = None) -> list[SessionTreeEntry]:
        leaf_id = from_id if from_id is not None else await self._storage.getLeafId()
        return await self._storage.getPathToRoot(leaf_id)

    async def build_context(self) -> SessionContext:
        return build_session_context(await self.get_branch())

    async def get_label(self, entry_id: str) -> str | None:
        return await self._storage.getLabel(entry_id)

    async def get_session_name(self) -> str | None:
        entries = await self._storage.find_entries("session_info")
        if not entries:
            return None
        last = entries[-1]
        name = getattr(last, "name", None)
        return name.strip() if name else None

    async def _append_typed_entry(self, entry: SessionTreeEntry) -> str:
        await self._storage.appendEntry(entry)
        return entry.id

    async def append_message(self, message: AgentMessage) -> str:
        entry_id = await self._storage.createEntryId()
        return await self._append_typed_entry(
            MessageEntry(
                type="message",
                id=entry_id,
                parentId=await self._get_append_parent_id(),
                timestamp=_now_iso(),
                message=message,
            )
        )

    async def append_thinking_level_change(self, thinking_level: str) -> str:
        entry_id = await self._storage.createEntryId()
        return await self._append_typed_entry(
            ThinkingLevelChangeEntry(
                type="thinking_level_change",
                id=entry_id,
                parentId=await self._get_append_parent_id(),
                timestamp=_now_iso(),
                thinkingLevel=thinking_level,
            )
        )

    async def append_model_change(self, provider: str, model_id: str) -> str:
        entry_id = await self._storage.createEntryId()
        return await self._append_typed_entry(
            ModelChangeEntry(
                type="model_change",
                id=entry_id,
                parentId=await self._get_append_parent_id(),
                timestamp=_now_iso(),
                provider=provider,
                modelId=model_id,
            )
        )

    async def append_compaction(
        self,
        summary: str,
        first_kept_entry_id: str,
        tokens_before: int,
        details: Any | None = None,
        from_hook: bool | None = None,
    ) -> str:
        entry_id = await self._storage.createEntryId()
        return await self._append_typed_entry(
            CompactionEntry(
                type="compaction",
                id=entry_id,
                parentId=await self._get_append_parent_id(),
                timestamp=_now_iso(),
                summary=summary,
                firstKeptEntryId=first_kept_entry_id,
                tokensBefore=tokens_before,
                details=details,
                fromHook=from_hook,
            )
        )

    async def append_custom_entry(self, custom_type: str, data: Any | None = None) -> str:
        entry_id = await self._storage.createEntryId()
        return await self._append_typed_entry(
            CustomEntry(
                type="custom",
                id=entry_id,
                parentId=await self._get_append_parent_id(),
                timestamp=_now_iso(),
                customType=custom_type,
                data=data,
            )
        )

    async def append_custom_message_entry(
        self,
        custom_type: str,
        content: Any,
        display: bool,
        details: Any | None = None,
    ) -> str:
        entry_id = await self._storage.createEntryId()
        return await self._append_typed_entry(
            CustomMessageEntry(
                type="custom_message",
                id=entry_id,
                parentId=await self._get_append_parent_id(),
                timestamp=_now_iso(),
                customType=custom_type,
                content=content,
                display=display,
                details=details,
            )
        )

    async def append_label(self, target_id: str, label: str | None) -> str:
        if await self._storage.getEntry(target_id) is None:
            raise SessionError("not_found", f"Entry {target_id} not found")
        entry_id = await self._storage.createEntryId()
        return await self._append_typed_entry(
            LabelEntry(
                type="label",
                id=entry_id,
                parentId=await self._get_append_parent_id(),
                timestamp=_now_iso(),
                targetId=target_id,
                label=label,
            )
        )

    async def append_session_name(self, name: str) -> str:
        entry_id = await self._storage.createEntryId()
        return await self._append_typed_entry(
            SessionInfoEntry(
                type="session_info",
                id=entry_id,
                parentId=await self._get_append_parent_id(),
                timestamp=_now_iso(),
                name=name.strip(),
            )
        )

    async def move_to(
        self,
        entry_id: str | None,
        summary: dict[str, Any] | None = None,
    ) -> str | None:
        if entry_id is not None and await self._storage.getEntry(entry_id) is None:
            raise SessionError("not_found", f"Entry {entry_id} not found")
        await self._storage.setLeafId(entry_id)
        if not summary:
            return None
        entry_id_val = await self._storage.createEntryId()
        return await self._append_typed_entry(
            BranchSummaryEntry(
                type="branch_summary",
                id=entry_id_val,
                parentId=entry_id,
                timestamp=_now_iso(),
                fromId=entry_id or "root",
                summary=summary.get("summary", ""),
                details=summary.get("details"),
                fromHook=summary.get("fromHook"),
            )
        )
