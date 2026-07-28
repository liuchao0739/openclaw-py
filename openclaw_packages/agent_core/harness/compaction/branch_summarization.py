from __future__ import annotations

import time
from typing import Any

from openclaw.llm.core import Model

from ...agent_types import AgentMessage
from ...runtime_deps import resolve_agent_core_complete_fn
from ..harness_types import (
    BranchSummaryError,
    BranchSummaryResult,
    SessionTreeEntry,
)
from openclaw_packages.agent_core.harness.session.session import Session
from ..messages import (
    as_agent_message,
    create_branch_summary_message,
    create_compaction_summary_message,
    create_custom_message,
    convert_to_llm,
)
from .compaction import _estimate_tokens, SUMMARIZATION_SYSTEM_PROMPT
from .utils import (
    compute_file_lists,
    create_file_ops,
    extract_file_ops_from_message,
    format_file_operations,
    serialize_conversation,
    FileOperations,
)


class BranchSummaryDetails:
    def __init__(self, read_files: list[str], modified_files: list[str]) -> None:
        self.read_files = read_files
        self.modified_files = modified_files


class BranchPreparation:
    def __init__(
        self,
        messages: list[AgentMessage],
        file_ops: FileOperations,
        total_tokens: int,
    ) -> None:
        self.messages = messages
        self.fileOps = file_ops
        self.totalTokens = total_tokens


class CollectEntriesResult:
    def __init__(
        self,
        entries: list[SessionTreeEntry],
        common_ancestor_id: str | None,
    ) -> None:
        self.entries = entries
        self.commonAncestorId = common_ancestor_id


class CollectBranchPathEntriesResult:
    def __init__(
        self,
        entries: list[Any],
        common_ancestor_id: str | None,
    ) -> None:
        self.entries = entries
        self.commonAncestorId = common_ancestor_id


class BranchPathEntry:
    def __init__(self, entry_id: str, parent_id: str | None) -> None:
        self.id = entry_id
        self.parentId = parent_id


BRANCH_SUMMARY_PREAMBLE = """The user explored a different conversation branch before returning here.
Summary of that exploration:

"""

BRANCH_SUMMARY_PROMPT = """Create a structured summary of this conversation branch for context when returning later.

Use this EXACT format:

## Goal
[What was the user trying to accomplish in this branch?]

## Constraints & Preferences
- [Any constraints, preferences, or requirements mentioned]
- [Or "(none)" if none were mentioned]

## Progress
### Done
- [x] [Completed tasks/changes]

### In Progress
- [ ] [Work that was started but not finished]

### Blocked
- [Issues preventing progress, if any]

## Key Decisions
- **[Decision]**: [Brief rationale]

## Next Steps
1. [What should happen next to continue this work]

Keep each section concise. Preserve exact file paths, function names, and error messages."""


def collect_entries_for_branch_summary_from_branches(
    old_branch: list[BranchPathEntry],
    target_branch: list[BranchPathEntry],
) -> CollectBranchPathEntriesResult:
    old_path = {entry.id for entry in old_branch}
    common_ancestor_id: str | None = None
    for entry in reversed(target_branch):
        if entry.id in old_path:
            common_ancestor_id = entry.id
            break
    first_summarized_index = (
        0
        if common_ancestor_id is None
        else next(
            (i for i, e in enumerate(old_branch) if e.id == common_ancestor_id),
            -1,
        )
        + 1
    )
    return CollectBranchPathEntriesResult(
        entries=old_branch[first_summarized_index:],
        common_ancestor_id=common_ancestor_id,
    )


async def collect_entries_for_branch_summary(
    session: Session,
    old_leaf_id: str | None,
    target_id: str,
) -> CollectEntriesResult:
    if not old_leaf_id:
        return CollectEntriesResult(entries=[], common_ancestor_id=None)
    old_branch = await session.get_branch(old_leaf_id)
    target_path = await session.get_branch(target_id)
    old_entries = [
        BranchPathEntry(
            entry.id,
            getattr(entry, "parentId", None),
        )
        for entry in old_branch
    ]
    target_entries = [
        BranchPathEntry(
            entry.id,
            getattr(entry, "parentId", None),
        )
        for entry in target_path
    ]
    result = collect_entries_for_branch_summary_from_branches(
        old_entries, target_entries
    )
    return CollectEntriesResult(
        entries=old_branch[-len(result.entries):] if result.entries else [],
        common_ancestor_id=result.commonAncestorId,
    )


def _get_message_from_entry(entry: SessionTreeEntry) -> AgentMessage | None:
    if entry.type == "message":
        if isinstance(entry.message, dict) and entry.message.get("role") == "toolResult":
            return None
        return entry.message
    if entry.type == "custom_message":
        return as_agent_message(
            create_custom_message(
                entry.customType,
                entry.content,
                entry.display,
                entry.details,
                entry.timestamp,
            )
        )
    if entry.type == "branch_summary":
        return as_agent_message(
            create_branch_summary_message(
                entry.summary, entry.fromId, entry.timestamp
            )
        )
    if entry.type == "compaction":
        return as_agent_message(
            create_compaction_summary_message(
                entry.summary, entry.tokensBefore, entry.timestamp
            )
        )
    return None


def prepare_branch_entries(
    entries: list[SessionTreeEntry],
    token_budget: int = 0,
) -> BranchPreparation:
    messages: list[AgentMessage] = []
    file_ops = create_file_ops()
    total_tokens = 0

    for entry in entries:
        if entry.type == "branch_summary" and not entry.fromHook and entry.details:
            details = entry.details
            if hasattr(details, "readFiles"):
                for f in details.readFiles:
                    file_ops.read.add(f)
            if hasattr(details, "modifiedFiles"):
                for f in details.modifiedFiles:
                    file_ops.edited.add(f)

    for i in range(len(entries) - 1, -1, -1):
        entry = entries[i]
        message = _get_message_from_entry(entry)
        if message is None:
            continue
        extract_file_ops_from_message(message, file_ops)
        tokens = _estimate_tokens(message)
        if token_budget > 0 and total_tokens + tokens > token_budget:
            if entry.type in ("compaction", "branch_summary"):
                if total_tokens < token_budget * 0.9:
                    messages.insert(0, message)
                    total_tokens += tokens
            break
        messages.insert(0, message)
        total_tokens += tokens
    return BranchPreparation(
        messages=messages,
        file_ops=file_ops,
        total_tokens=total_tokens,
    )


async def generate_branch_summary(
    entries: list[SessionTreeEntry],
    options: dict[str, Any],
) -> BranchSummaryResult:
    model: Model = options["model"]
    api_key: str = options["apiKey"]
    headers = options.get("headers")
    signal = options.get("signal")
    custom_instructions = options.get("customInstructions")
    replace_instructions = options.get("replaceInstructions", False)
    reserve_tokens = options.get("reserveTokens", 16384)
    stream_fn = options.get("streamFn")
    runtime = options.get("runtime")

    context_window = model.context_window or 128000
    token_budget = context_window - reserve_tokens

    preparation = prepare_branch_entries(entries, token_budget)
    messages = preparation.messages
    file_ops = preparation.fileOps

    if not messages:
        return BranchSummaryResult(
            summary="No content to summarize",
            read_files=[],
            modified_files=[],
        )

    llm_messages = convert_to_llm(messages)
    conversation_text = serialize_conversation(llm_messages)

    if replace_instructions and custom_instructions:
        instructions = custom_instructions
    elif custom_instructions:
        instructions = f"{BRANCH_SUMMARY_PROMPT}\n\nAdditional focus: {custom_instructions}"
    else:
        instructions = BRANCH_SUMMARY_PROMPT

    prompt_text = f"<conversation>\n{conversation_text}\n</conversation>\n\n{instructions}"
    summarization_messages = [
        {
            "role": "user",
            "content": [{"type": "text", "text": prompt_text}],
            "timestamp": int(time.time() * 1000),
        }
    ]
    context = {
        "systemPrompt": SUMMARIZATION_SYSTEM_PROMPT,
        "messages": summarization_messages,
    }
    stream_options = {
        "apiKey": api_key,
        "headers": headers,
        "signal": signal,
        "maxTokens": 2048,
    }

    if stream_fn is not None:
        stream = stream_fn(model, context, stream_options)
        result = stream.result()
        if hasattr(result, "__await__"):
            result = await result
        response = result
    else:
        complete_fn = resolve_agent_core_complete_fn(runtime)
        response = await complete_fn(model, context, stream_options)

    if response.get("stopReason") == "aborted":
        raise BranchSummaryError(
            "aborted",
            response.get("errorMessage") or "Branch summary aborted",
        )
    if response.get("stopReason") == "error":
        raise BranchSummaryError(
            "summarization_failed",
            f"Branch summary failed: {response.get('errorMessage') or 'Unknown error'}",
        )
    content = response.get("content", [])
    if isinstance(content, list):
        summary = "\n".join(
            c.get("text", "")
            for c in content
            if isinstance(c, dict) and c.get("type") == "text"
        )
    else:
        summary = str(content)
    summary = BRANCH_SUMMARY_PREAMBLE + summary
    read_files, modified_files = compute_file_lists(file_ops)
    summary += format_file_operations(read_files, modified_files)
    return BranchSummaryResult(
        summary=summary or "No summary generated",
        read_files=read_files,
        modified_files=modified_files,
    )
