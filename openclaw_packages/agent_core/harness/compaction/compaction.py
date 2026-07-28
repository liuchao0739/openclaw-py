from __future__ import annotations

import asyncio
import time
from typing import Any

from openclaw.llm.core import (
    AssistantMessage,
    Model,
    Usage,
)

from ...agent_types import AgentMessage
from ..harness_types import (
    CompactionEntry,
    CompactionError,
    CompactionSettings,
    SessionTreeEntry,
)
from ..messages import (
    as_agent_message,
    create_branch_summary_message,
    create_compaction_summary_message,
    create_custom_message,
    convert_to_llm,
)
from openclaw_packages.agent_core.harness.session.session import build_session_context
from openclaw_packages.agent_core.harness.session.timestamps import parse_session_timestamp_ms
from .utils import (
    compute_file_lists,
    create_file_ops,
    extract_file_ops_from_message,
    format_file_operations,
    serialize_conversation,
    FileOperations,
)


DEFAULT_COMPACTION_SETTINGS: CompactionSettings = CompactionSettings(
    enabled=True,
    reserveTokens=16384,
    keepRecentTokens=20000,
)

IMAGE_BLOCK_CHARS = 4800

SUMMARIZATION_SYSTEM_PROMPT = (
    "You are a context summarization assistant. Your task is to read a conversation "
    "between a user and an AI coding assistant, then produce a structured summary "
    "following the exact format specified.\n\n"
    "Do NOT continue the conversation. Do NOT respond to any questions in the "
    "conversation. ONLY output the structured summary."
)

SUMMARIZATION_PROMPT = (
    "The messages above are a conversation to summarize. Create a structured context "
    "checkpoint summary that another LLM will use to continue the work.\n\n"
    "Use this EXACT format:\n\n"
    "## Goal\n[What is the user trying to accomplish? Can be multiple items if the session covers different tasks.]\n\n"
    "## Constraints & Preferences\n- [Any constraints, preferences, or requirements mentioned by user]\n"
    "- [Or \"(none)\" if none were mentioned]\n\n"
    "## Progress\n### Done\n- [x] [Completed tasks/changes]\n\n"
    "### In Progress\n- [ ] [Current work]\n\n"
    "### Blocked\n- [Issues preventing progress, if any]\n\n"
    "## Key Decisions\n- **[Decision]**: [Brief rationale]\n\n"
    "## Next Steps\n1. [Ordered list of what should happen next]\n\n"
    "## Critical Context\n- [Any data, examples, or references needed to continue]\n"
    "- [Or \"(none)\" if not applicable]\n\n"
    "Keep each section concise. Preserve exact file paths, function names, and error messages."
)

UPDATE_SUMMARIZATION_PROMPT = (
    "The messages above are NEW conversation messages to incorporate into the "
    "existing summary provided in <previous-summary> tags.\n\n"
    "Update the existing structured summary with new information. RULES:\n"
    "- PRESERVE all existing information from the previous summary\n"
    "- ADD new progress, decisions, and context from the new messages\n"
    "- UPDATE the Progress section: move items from \"In Progress\" to \"Done\" when completed\n"
    "- UPDATE \"Next Steps\" based on what was accomplished\n"
    "- PRESERVE exact file paths, function names, and error messages\n"
    "- If something is no longer relevant, you may remove it\n\n"
    "Use this EXACT format:\n\n"
    "## Goal\n[Preserve existing goals, add new ones if the task expanded]\n\n"
    "## Constraints & Preferences\n- [Preserve existing, add new ones discovered]\n\n"
    "## Progress\n### Done\n- [x] [Include previously done items AND newly completed items]\n\n"
    "### In Progress\n- [ ] [Current work - update based on progress]\n\n"
    "### Blocked\n- [Current blockers - remove if resolved]\n\n"
    "## Key Decisions\n- **[Decision]**: [Brief rationale] (preserve all previous, add new)\n\n"
    "## Next Steps\n1. [Update based on current state]\n\n"
    "## Critical Context\n- [Preserve important context, add new if needed]\n\n"
    "Keep each section concise. Preserve exact file paths, function names, and error messages."
)

TURN_PREFIX_SUMMARIZATION_PROMPT = (
    "This is the PREFIX of a turn that was too large to keep. The SUFFIX (recent work) is retained.\n\n"
    "Summarize the prefix to provide context for the retained suffix:\n\n"
    "## Original Request\n[What did the user ask for in this turn?]\n\n"
    "## Early Progress\n- [Key decisions and work done in the prefix]\n\n"
    "## Context for Suffix\n- [Information needed to understand the retained recent work]\n\n"
    "Be concise. Focus on what's needed to understand the kept suffix."
)


class CompactionDetails:
    def __init__(self, read_files: list[str], modified_files: list[str]) -> None:
        self.read_files = read_files
        self.modified_files = modified_files


class CompactionResult:
    def __init__(
        self,
        summary: str,
        first_kept_entry_id: str,
        tokens_before: int,
        details: CompactionDetails | None = None,
    ) -> None:
        self.summary = summary
        self.firstKeptEntryId = first_kept_entry_id
        self.tokensBefore = tokens_before
        self.details = details


class CutPointResult:
    def __init__(
        self,
        first_kept_entry_index: int,
        turn_start_index: int,
        is_split_turn: bool,
    ) -> None:
        self.firstKeptEntryIndex = first_kept_entry_index
        self.turnStartIndex = turn_start_index
        self.isSplitTurn = is_split_turn


class CompactionPreparation:
    def __init__(
        self,
        first_kept_entry_id: str,
        messages_to_summarize: list[AgentMessage],
        turn_prefix_messages: list[AgentMessage],
        is_split_turn: bool,
        tokens_before: int,
        file_ops: FileOperations,
        settings: CompactionSettings,
        previous_summary: str | None = None,
    ) -> None:
        self.firstKeptEntryId = first_kept_entry_id
        self.messagesToSummarize = messages_to_summarize
        self.turnPrefixMessages = turn_prefix_messages
        self.isSplitTurn = is_split_turn
        self.tokensBefore = tokens_before
        self.previousSummary = previous_summary
        self.fileOps = file_ops
        self.settings = settings


def calculate_context_tokens(usage: Usage) -> int:
    if usage.total_tokens:
        return usage.total_tokens
    return usage.input + usage.output + usage.cache_read + usage.cache_write


def _get_assistant_usage(msg: AgentMessage) -> Usage | None:
    if msg.get("role") != "assistant":
        return None
    if msg.get("stopReason") in ("aborted", "error"):
        return None
    usage = msg.get("usage")
    if usage is None:
        return None
    return usage


def get_last_assistant_usage(entries: list[SessionTreeEntry]) -> Usage | None:
    for entry in reversed(entries):
        if entry.type == "message":
            usage = _get_assistant_usage(entry.message)
            if usage is not None:
                return usage
    return None


class ContextUsageEstimate:
    def __init__(
        self,
        tokens: int,
        usage_tokens: int,
        trailing_tokens: int,
        last_usage_index: int | None,
    ) -> None:
        self.tokens = tokens
        self.usageTokens = usage_tokens
        self.trailingTokens = trailing_tokens
        self.lastUsageIndex = last_usage_index


def _get_last_assistant_usage_info(
    messages: list[AgentMessage],
) -> tuple[Usage, int] | None:
    for i in range(len(messages) - 1, -1, -1):
        usage = _get_assistant_usage(messages[i])
        if usage is not None:
            return (usage, i)
    return None


def _estimate_tokens(message: AgentMessage) -> int:
    content = message.get("content")
    role = message.get("role")
    if role == "user":
        if isinstance(content, str):
            return max(1, len(content) // 4)
        chars = _count_content_block_chars(content or [])
        return max(1, chars // 4)
    if role == "assistant":
        chars = 0
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype == "text":
                    chars += len(block.get("text", ""))
                elif btype == "thinking":
                    chars += len(block.get("thinking", ""))
                elif btype == "toolCall":
                    args = block.get("arguments", {})
                    import json
                    try:
                        args_str = json.dumps(args)
                    except (TypeError, ValueError):
                        args_str = str(args)
                    chars += len(block.get("name", "")) + len(args_str)
        return max(1, chars // 4)
    if role in ("custom", "toolResult"):
        if isinstance(content, str):
            return max(1, len(content) // 4)
        chars = _count_content_block_chars(content or [])
        return max(1, chars // 4)
    if role == "bashExecution":
        chars = len(message.get("command", "")) + len(message.get("output", ""))
        return max(1, chars // 4)
    if role in ("branchSummary", "compactionSummary"):
        chars = len(message.get("summary", ""))
        return max(1, chars // 4)
    return 0


def _count_content_block_chars(content: list[Any]) -> int:
    chars = 0
    for block in content:
        if not isinstance(block, dict):
            continue
        btype = block.get("type")
        if btype == "text":
            chars += len(block.get("text", ""))
        elif btype == "image":
            chars += IMAGE_BLOCK_CHARS
    return chars


def estimate_context_tokens(messages: list[AgentMessage]) -> ContextUsageEstimate:
    usage_info = _get_last_assistant_usage_info(messages)
    if usage_info is None:
        estimated = sum(_estimate_tokens(m) for m in messages)
        return ContextUsageEstimate(
            tokens=estimated,
            usage_tokens=0,
            trailing_tokens=estimated,
            last_usage_index=None,
        )
    usage, index = usage_info
    usage_tokens = calculate_context_tokens(usage)
    trailing_tokens = sum(
        _estimate_tokens(m) for m in messages[index + 1:]
    )
    return ContextUsageEstimate(
        tokens=usage_tokens + trailing_tokens,
        usage_tokens=usage_tokens,
        trailing_tokens=trailing_tokens,
        last_usage_index=index,
    )


def should_compact(
    context_tokens: int,
    context_window: int,
    settings: CompactionSettings,
) -> bool:
    if not settings.enabled:
        return False
    return context_tokens > context_window - settings.reserveTokens


def _find_valid_cut_points(
    entries: list[SessionTreeEntry],
    start_index: int,
    end_index: int,
) -> list[int]:
    cut_points: list[int] = []
    for i in range(start_index, end_index):
        entry = entries[i]
        if entry.type == "message":
            role = entry.message.get("role") if isinstance(entry.message, dict) else None
            if role in (
                "bashExecution",
                "custom",
                "branchSummary",
                "compactionSummary",
                "user",
                "assistant",
            ):
                cut_points.append(i)
        if entry.type in ("branch_summary", "custom_message"):
            cut_points.append(i)
    return cut_points


def find_turn_start_index(
    entries: list[SessionTreeEntry],
    entry_index: int,
    start_index: int,
) -> int:
    for i in range(entry_index, start_index - 1, -1):
        entry = entries[i]
        if entry.type in ("branch_summary", "custom_message"):
            return i
        if entry.type == "message":
            role = entry.message.get("role") if isinstance(entry.message, dict) else None
            if role in ("user", "bashExecution"):
                return i
    return -1


def find_cut_point(
    entries: list[SessionTreeEntry],
    start_index: int,
    end_index: int,
    keep_recent_tokens: int,
) -> CutPointResult:
    cut_points = _find_valid_cut_points(entries, start_index, end_index)
    if not cut_points:
        return CutPointResult(
            first_kept_entry_index=start_index,
            turn_start_index=-1,
            is_split_turn=False,
        )
    accumulated = 0
    cut_index = cut_points[0]
    for i in range(end_index - 1, start_index - 1, -1):
        entry = entries[i]
        if entry.type != "message":
            continue
        accumulated += _estimate_tokens(entry.message)
        if accumulated >= keep_recent_tokens:
            cut_index = cut_points[-1]
            for cp in cut_points:
                if cp >= i:
                    cut_index = cp
                    break
            break
    while cut_index > start_index:
        prev = entries[cut_index - 1]
        if prev.type in ("compaction", "message"):
            break
        cut_index -= 1
    cut_entry = entries[cut_index]
    is_user_message = (
        cut_entry.type == "message"
        and (cut_entry.message.get("role") if isinstance(cut_entry.message, dict) else None) == "user"
    )
    turn_start_index = (
        -1
        if is_user_message
        else find_turn_start_index(entries, cut_index, start_index)
    )
    return CutPointResult(
        first_kept_entry_index=cut_index,
        turn_start_index=turn_start_index,
        is_split_turn=not is_user_message and turn_start_index != -1,
    )


def _get_message_from_entry(entry: SessionTreeEntry) -> AgentMessage | None:
    if entry.type == "message":
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


def _get_message_from_entry_for_compaction(
    entry: SessionTreeEntry,
) -> AgentMessage | None:
    if entry.type == "compaction":
        return None
    return _get_message_from_entry(entry)


def _extract_file_operations(
    messages: list[AgentMessage],
    entries: list[SessionTreeEntry],
    prev_compaction_index: int,
) -> FileOperations:
    file_ops = create_file_ops()
    if prev_compaction_index >= 0:
        prev = entries[prev_compaction_index]
        if prev.type == "compaction" and not prev.fromHook and prev.details:
            details = prev.details
            if hasattr(details, "readFiles"):
                for f in details.readFiles:
                    file_ops.read.add(f)
            if hasattr(details, "modifiedFiles"):
                for f in details.modifiedFiles:
                    file_ops.edited.add(f)
    for msg in messages:
        extract_file_ops_from_message(msg, file_ops)
    return file_ops


def prepare_compaction(
    path_entries: list[SessionTreeEntry],
    settings: CompactionSettings,
) -> CompactionPreparation | None:
    if not path_entries or path_entries[-1].type == "compaction":
        return None

    prev_compaction_index = -1
    for i in range(len(path_entries) - 1, -1, -1):
        if path_entries[i].type == "compaction":
            prev_compaction_index = i
            break

    previous_summary: str | None = None
    boundary_start = 0
    if prev_compaction_index >= 0:
        prev = path_entries[prev_compaction_index]
        previous_summary = prev.summary
        first_kept_idx = next(
            (i for i, e in enumerate(path_entries) if e.id == prev.firstKeptEntryId),
            -1,
        )
        boundary_start = first_kept_idx if first_kept_idx >= 0 else prev_compaction_index + 1

    boundary_end = len(path_entries)
    tokens_before = estimate_context_tokens(
        build_session_context(path_entries).messages
    ).tokens

    cut_point = find_cut_point(
        path_entries, boundary_start, boundary_end, settings.keepRecentTokens
    )
    first_kept_entry = path_entries[cut_point.firstKeptEntryIndex]
    if not getattr(first_kept_entry, "id", None):
        raise CompactionError(
            "invalid_session",
            "First kept entry has no UUID - session may need migration",
        )
    first_kept_entry_id = first_kept_entry.id

    history_end = (
        cut_point.turnStartIndex
        if cut_point.isSplitTurn
        else cut_point.firstKeptEntryIndex
    )
    messages_to_summarize: list[AgentMessage] = []
    for i in range(boundary_start, history_end):
        msg = _get_message_from_entry_for_compaction(path_entries[i])
        if msg is not None:
            messages_to_summarize.append(msg)

    turn_prefix_messages: list[AgentMessage] = []
    if cut_point.isSplitTurn:
        for i in range(cut_point.turnStartIndex, cut_point.firstKeptEntryIndex):
            msg = _get_message_from_entry_for_compaction(path_entries[i])
            if msg is not None:
                turn_prefix_messages.append(msg)

    file_ops = _extract_file_operations(
        messages_to_summarize, path_entries, prev_compaction_index
    )
    if cut_point.isSplitTurn:
        for msg in turn_prefix_messages:
            extract_file_ops_from_message(msg, file_ops)

    return CompactionPreparation(
        first_kept_entry_id=first_kept_entry_id,
        messages_to_summarize=messages_to_summarize,
        turn_prefix_messages=turn_prefix_messages,
        is_split_turn=cut_point.isSplitTurn,
        tokens_before=tokens_before,
        previous_summary=previous_summary,
        file_ops=file_ops,
        settings=settings,
    )


async def _complete_summarization(
    model: Model,
    context: Any,
    options: dict[str, Any],
    stream_fn: Any = None,
    runtime: Any = None,
) -> AssistantMessage:
    from ...runtime_deps import resolve_agent_core_complete_fn
    if stream_fn is not None:
        stream = stream_fn(model, context, options)
        if hasattr(stream, "result"):
            result = stream.result()
            if hasattr(result, "__await__"):
                result = await result
            return result
    complete_fn = resolve_agent_core_complete_fn(runtime)
    return await complete_fn(model, context, options)


async def generate_summary(
    current_messages: list[AgentMessage],
    model: Model,
    reserve_tokens: int,
    api_key: str | None,
    headers: dict[str, str] | None = None,
    signal: Any | None = None,
    custom_instructions: str | None = None,
    previous_summary: str | None = None,
    thinking_level: str | None = None,
    stream_fn: Any = None,
    runtime: Any = None,
) -> str:
    max_tokens = min(
        int(0.8 * reserve_tokens),
        model.max_tokens if model.max_tokens > 0 else 10**12,
    )
    base_prompt = (
        UPDATE_SUMMARIZATION_PROMPT if previous_summary else SUMMARIZATION_PROMPT
    )
    if custom_instructions:
        base_prompt = f"{base_prompt}\n\nAdditional focus: {custom_instructions}"
    llm_messages = convert_to_llm(current_messages)
    conversation_text = serialize_conversation(llm_messages)
    prompt_text = f"<conversation>\n{conversation_text}\n</conversation>\n\n"
    if previous_summary:
        prompt_text += (
            f"<previous-summary>\n{previous_summary}\n</previous-summary>\n\n"
        )
    prompt_text += base_prompt

    summarization_messages = [
        {
            "role": "user",
            "content": [{"type": "text", "text": prompt_text}],
            "timestamp": int(time.time() * 1000),
        }
    ]

    options: dict[str, Any] = {
        "maxTokens": max_tokens,
        "signal": signal,
        "apiKey": api_key,
        "headers": headers,
    }
    response = await _complete_summarization(
        model,
        {
            "systemPrompt": SUMMARIZATION_SYSTEM_PROMPT,
            "messages": summarization_messages,
        },
        options,
        stream_fn,
        runtime,
    )
    if response.get("stopReason") == "aborted":
        raise CompactionError(
            "aborted",
            response.get("errorMessage") or "Summarization aborted",
        )
    if response.get("stopReason") == "error":
        raise CompactionError(
            "summarization_failed",
            f"Summarization failed: {response.get('errorMessage') or 'Unknown error'}",
        )
    content = response.get("content", [])
    if isinstance(content, list):
        text = "\n".join(
            c.get("text", "")
            for c in content
            if isinstance(c, dict) and c.get("type") == "text"
        )
    else:
        text = str(content)
    return text


async def _generate_turn_prefix_summary(
    messages: list[AgentMessage],
    model: Model,
    reserve_tokens: int,
    api_key: str | None,
    headers: dict[str, str] | None = None,
    signal: Any | None = None,
    thinking_level: str | None = None,
    stream_fn: Any = None,
    runtime: Any = None,
) -> str:
    max_tokens = min(
        int(0.5 * reserve_tokens),
        model.max_tokens if model.max_tokens > 0 else 10**12,
    )
    llm_messages = convert_to_llm(messages)
    conversation_text = serialize_conversation(llm_messages)
    prompt_text = f"<conversation>\n{conversation_text}\n</conversation>\n\n{TURN_PREFIX_SUMMARIZATION_PROMPT}"
    summarization_messages = [
        {
            "role": "user",
            "content": [{"type": "text", "text": prompt_text}],
            "timestamp": int(time.time() * 1000),
        }
    ]
    options: dict[str, Any] = {
        "maxTokens": max_tokens,
        "signal": signal,
        "apiKey": api_key,
        "headers": headers,
    }
    response = await _complete_summarization(
        model,
        {
            "systemPrompt": SUMMARIZATION_SYSTEM_PROMPT,
            "messages": summarization_messages,
        },
        options,
        stream_fn,
        runtime,
    )
    if response.get("stopReason") == "aborted":
        raise CompactionError(
            "aborted",
            response.get("errorMessage") or "Turn prefix summarization aborted",
        )
    if response.get("stopReason") == "error":
        raise CompactionError(
            "summarization_failed",
            f"Turn prefix summarization failed: {response.get('errorMessage') or 'Unknown error'}",
        )
    content = response.get("content", [])
    if isinstance(content, list):
        return "\n".join(
            c.get("text", "")
            for c in content
            if isinstance(c, dict) and c.get("type") == "text"
        )
    return str(content)


async def compact(
    preparation: CompactionPreparation,
    model: Model,
    api_key: str | None,
    headers: dict[str, str] | None = None,
    custom_instructions: str | None = None,
    signal: Any | None = None,
    thinking_level: str | None = None,
    stream_fn: Any = None,
    runtime: Any = None,
) -> CompactionResult:
    if not preparation.firstKeptEntryId:
        raise CompactionError(
            "invalid_session",
            "First kept entry has no UUID - session may need migration",
        )
    if preparation.isSplitTurn and preparation.turnPrefixMessages:
        tasks = []
        if preparation.messagesToSummarize:
            tasks.append(
                generate_summary(
                    preparation.messagesToSummarize,
                    model,
                    preparation.settings.reserveTokens,
                    api_key,
                    headers,
                    signal,
                    custom_instructions,
                    preparation.previousSummary,
                    thinking_level,
                    stream_fn,
                    runtime,
                )
            )
        else:
            async def _noop() -> str:
                return "No prior history."
            tasks.append(_noop())
        tasks.append(
            _generate_turn_prefix_summary(
                preparation.turnPrefixMessages,
                model,
                preparation.settings.reserveTokens,
                api_key,
                headers,
                signal,
                thinking_level,
                stream_fn,
                runtime,
            )
        )
        history_result, turn_prefix_result = await asyncio.gather(*tasks)
        summary = (
            f"{history_result}\n\n---\n\n**Turn Context (split turn):**\n\n{turn_prefix_result}"
        )
    else:
        summary = await generate_summary(
            preparation.messagesToSummarize,
            model,
            preparation.settings.reserveTokens,
            api_key,
            headers,
            signal,
            custom_instructions,
            preparation.previousSummary,
            thinking_level,
            stream_fn,
            runtime,
        )
    read_files, modified_files = compute_file_lists(preparation.fileOps)
    summary += format_file_operations(read_files, modified_files)
    return CompactionResult(
        summary=summary,
        first_kept_entry_id=preparation.firstKeptEntryId,
        tokens_before=preparation.tokensBefore,
        details=CompactionDetails(read_files, modified_files),
    )
