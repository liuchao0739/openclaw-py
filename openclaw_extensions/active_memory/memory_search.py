from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from openclaw_extensions.active_memory.config import (
    ACTIVE_MEMORY_CLOSE_TAG,
    ACTIVE_MEMORY_OPEN_TAG,
    ACTIVE_MEMORY_PLUGIN_TAG,
    ACTIVE_MEMORY_UNTRUSTED_CONTEXT_HEADER,
    ActiveMemoryPromptStyle,
    ActiveRecallPluginConfig,
    MAX_ACTIVE_MEMORY_SEARCH_QUERY_CHARS,
    NO_RECALL_VALUES,
    RECALLED_CONTEXT_LINE_PATTERNS,
    TIMEOUT_BOILERPLATE_PATTERNS,
    build_prompt_style_lines,
)


@dataclass
class ActiveRecallRecentTurn:
    role: str
    text: str


def build_recall_prompt(
    config: ActiveRecallPluginConfig,
    query: str,
    search_query: str,
) -> str:
    default_instructions = [
        "You are a memory search agent.",
        "Another model is preparing the final user-facing answer.",
        "Your job is to search memory and return only the most relevant memory context for that model.",
        "You receive a bounded search query plus conversation context, including the user's latest message.",
        "Use only the available memory tools.",
        "Use the bounded search query with the configured memory tools.",
        f"Configured memory tools: {', '.join(config.tools_allow)}.",
        "Do not use channel metadata, provider metadata, debug output, or the full conversation context as the memory tool query.",
        "If the available memory tools find nothing useful, reply with NONE.",
        "When searching for preference or habit recall, use permissive search limits or thresholds before deciding that no useful memory exists.",
        "Do not answer the user directly.",
        f"Prompt style: {config.prompt_style}.",
        *build_prompt_style_lines(config.prompt_style),
        "If the user is directly asking about favorites, preferences, habits, routines, or personal facts, treat that as a strong recall signal.",
        "Questions like 'what is my favorite food', 'do you remember my flight preferences', or 'what do i usually get' should normally return memory when relevant results exist.",
        "If the provided conversation context already contains recalled-memory summaries, debug output, or prior memory/tool traces, ignore that surfaced text unless the latest user message clearly requires re-checking it.",
        "Return memory only when it would materially help the other model answer the user's latest message.",
        "If the connection is weak, broad, or only vaguely related, reply with NONE.",
        "If nothing clearly useful is found, reply with NONE.",
        "Return exactly one of these two forms:",
        "1. NONE",
        "2. one compact plain-text summary",
        f"If something is useful, reply with one compact plain-text summary under {config.max_summary_chars} characters total.",
        "Write the summary as a memory note about the user, not as a reply to the user.",
        "Do not explain your reasoning.",
        "Do not return bullets, numbering, labels, XML, JSON, or markdown list formatting.",
        "Do not prefix the summary with 'Memory:' or any other label.",
        "",
        "Good examples:",
        "User message: What is my favorite food?",
        "Return: User's favorite food is ramen; tacos also come up often.",
        "User message: Do you remember my flight preferences?",
        "Return: User prefers aisle seats and extra buffer over tight connections.",
        "Recent context: user was discussing flights and airport planning.",
        "Latest user message: I might see a movie while I wait for the flight.",
        "Return: User's favorite movie snack is buttery popcorn with extra salt.",
        "User message: Explain DNS over HTTPS.",
        "Return: NONE",
        "",
        "Bad examples:",
        "Return: - Favorite food is ramen",
        "Return: 1. Favorite food is ramen",
        "Return: Memory: Favorite food is ramen",
        'Return: {"memory":"Favorite food is ramen"}',
        "Return: <memory>Favorite food is ramen</memory>",
        "Return: Ramen seems to be your favorite food.",
        "Return: You like aisle seats and extra buffer.",
        "Return: I prefer aisle seats and extra buffer.",
        "Recent context: user was discussing flights and airport planning. Latest user message: I might see a movie while I wait for the flight. Return: User prefers aisle seats and extra buffer over tight connections.",
    ]
    instruction_block_parts = [default_instructions]
    if config.prompt_override:
        instruction_block_parts[0] = config.prompt_override
    if config.prompt_append:
        instruction_block_parts.append(f"Additional operator instructions:\n{config.prompt_append}")
    instruction_block = "\n\n".join(section for section in instruction_block_parts if section)
    return "\n\n".join([
        instruction_block,
        f"Bounded memory search query:\n{search_query}",
        f"Conversation context:\n{query}",
    ])


def build_query(
    latest_user_message: str,
    config: ActiveRecallPluginConfig,
    recent_turns: list[ActiveRecallRecentTurn] | None = None,
) -> str:
    latest = latest_user_message.strip()
    if config.query_mode == "message":
        return latest
    if config.query_mode == "full":
        all_turns = []
        for turn in (recent_turns or []):
            text = f"{turn.role}: {turn.text.strip()}".strip()
            text = re.sub(r"\s+", " ", text)
            if text:
                all_turns.append(text)
        if not all_turns:
            return latest
        return "\n".join(["Full conversation context:", *all_turns, "", "Latest user message:", latest])
    remaining_user = config.recent_user_turns
    remaining_assistant = config.recent_assistant_turns
    selected: list[ActiveRecallRecentTurn] = []
    turns = recent_turns or []
    for index in range(len(turns) - 1, -1, -1):
        turn = turns[index]
        if turn.role == "user":
            if remaining_user <= 0:
                continue
            remaining_user -= 1
            selected.append(ActiveRecallRecentTurn(
                role="user",
                text=re.sub(r"\s+", " ", turn.text.strip())[:config.recent_user_chars],
            ))
        else:
            if remaining_assistant <= 0:
                continue
            remaining_assistant -= 1
            selected.append(ActiveRecallRecentTurn(
                role="assistant",
                text=re.sub(r"\s+", " ", turn.text.strip())[:config.recent_assistant_chars],
            ))
    recent = [t for t in reversed(selected) if t.text]
    if not recent:
        return latest
    return "\n".join(["Recent conversation tail:", *[f"{t.role}: {t.text}" for t in recent], "", "Latest user message:", latest])


def strip_external_untrusted_blocks(text: str) -> str:
    return re.sub(
        r"<<<EXTERNAL_UNTRUSTED_CONTENT\b[^>]*>>>[\s\S]*?<<<END_EXTERNAL_UNTRUSTED_CONTENT\b[^>]*>>>",
        " ",
        text,
    )


def strip_json_fences(text: str) -> str:
    return re.sub(r"```(?:json)?\s*[\s\S]*?```", " ", text, flags=re.IGNORECASE)


def strip_active_memory_xml_blocks(text: str) -> str:
    return re.sub(r"<active_memory_plugin>[\s\S]*?</active_memory_plugin>", " ", text, flags=re.IGNORECASE)


def normalize_search_query_text(text: str) -> str:
    lines = text.split("\n")
    filtered: list[str] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if re.match(r"^(conversation info|sender|untrusted context)\b", line, re.IGNORECASE):
            continue
        if re.match(r"^(source: external|---|untrusted discord message body)$", line, re.IGNORECASE):
            continue
        if re.match(r"^⚠️?\s*Agent couldn't generate a response", line, re.IGNORECASE):
            continue
        if re.match(r"^Please try again\.?$", line, re.IGNORECASE):
            continue
        filtered.append(line)
    return " ".join(filtered)


def clamp_search_query(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) > MAX_ACTIVE_MEMORY_SEARCH_QUERY_CHARS:
        return normalized[:MAX_ACTIVE_MEMORY_SEARCH_QUERY_CHARS].strip()
    return normalized


def build_search_query(
    latest_user_message: str,
    recent_turns: list[ActiveRecallRecentTurn] | None = None,
) -> str:
    latest = clamp_search_query(
        normalize_search_query_text(
            strip_active_memory_xml_blocks(
                strip_json_fences(strip_external_untrusted_blocks(latest_user_message))
            )
        )
    )
    if len(latest) >= 12 or not recent_turns:
        return latest or clamp_search_query(latest_user_message)
    previous_user = None
    for turn in reversed(recent_turns):
        if turn.role == "user" and turn.text.strip() != latest_user_message.strip():
            previous_user = turn
            break
    if previous_user is None:
        return latest or clamp_search_query(latest_user_message)
    context = clamp_search_query(
        normalize_search_query_text(strip_recalled_context_noise(previous_user.text))
    )[:120].strip()
    return clamp_search_query(f"{context} {latest}" if context else latest)


def strip_recalled_context_noise(text: str) -> str:
    lines = text.split("\n")
    cleaned_lines: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line:
            continue
        if line == ACTIVE_MEMORY_UNTRUSTED_CONTEXT_HEADER:
            continue
        if line == ACTIVE_MEMORY_OPEN_TAG:
            close_index = -1
            for probe in range(i, len(lines)):
                if lines[probe].strip() == ACTIVE_MEMORY_CLOSE_TAG:
                    close_index = probe
                    break
            if close_index != -1:
                i = close_index + 1
                continue
        if line == ACTIVE_MEMORY_CLOSE_TAG:
            continue
        if any(pattern.search(line) for pattern in RECALLED_CONTEXT_LINE_PATTERNS):
            continue
        cleaned_lines.append(line)
    return " ".join(cleaned_lines)


def strip_injected_active_memory_prefix_only(text: str) -> str:
    lines = text.split("\n")
    cleaned_lines: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if line == ACTIVE_MEMORY_UNTRUSTED_CONTEXT_HEADER:
            if i < len(lines) and lines[i].strip() == ACTIVE_MEMORY_OPEN_TAG:
                close_index = -1
                for probe in range(i + 1, len(lines)):
                    if lines[probe].strip() == ACTIVE_MEMORY_CLOSE_TAG:
                        close_index = probe
                        break
                if close_index != -1:
                    i = close_index + 1
                    continue
        cleaned_lines.append(line)
    return " ".join(cleaned_lines)


def extract_recent_turns(messages: list[Any]) -> list[ActiveRecallRecentTurn]:
    turns: list[ActiveRecallRecentTurn] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        if role not in ("user", "assistant"):
            continue
        from openclaw_extensions.active_memory.transcript import extract_text_content
        raw_text = extract_text_content(message.get("content"))
        if role == "assistant":
            text = strip_recalled_context_noise(raw_text)
        else:
            text = strip_injected_active_memory_prefix_only(raw_text)
        if not text:
            continue
        turns.append(ActiveRecallRecentTurn(role=role, text=text))
    return turns


def normalize_no_recall_value(value: str) -> bool:
    return value.strip().lower() in NO_RECALL_VALUES


def is_timeout_boilerplate_summary(value: str) -> bool:
    return any(pattern.search(value) for pattern in TIMEOUT_BOILERPLATE_PATTERNS)


def normalize_active_summary(raw_reply: str) -> str | None:
    trimmed = raw_reply.strip()
    if normalize_no_recall_value(trimmed):
        return None
    single_line = re.sub(r"\s+", " ", trimmed).strip()
    if not single_line or normalize_no_recall_value(single_line) or is_timeout_boilerplate_summary(single_line):
        return None
    return single_line


def truncate_summary(summary: str, max_summary_chars: int) -> str:
    trimmed = summary.strip()
    if len(trimmed) <= max_summary_chars:
        return trimmed
    bounded = trimmed[:max_summary_chars].rstrip()
    next_char = trimmed[max_summary_chars] if max_summary_chars < len(trimmed) else ""
    if not next_char or next_char.isspace():
        return bounded
    last_boundary = bounded.rfind(" ")
    if last_boundary > 0:
        return bounded[:last_boundary].rstrip()
    return bounded


def build_plugin_status_line(result: dict[str, Any], config: ActiveRecallPluginConfig) -> str:
    parts = [
        "🧩 Active Memory:",
        f"status={result.get('status', 'unknown')}",
    ]
    elapsed = result.get("elapsedMs", 0)
    if isinstance(elapsed, (int, float)):
        if elapsed >= 1000:
            seconds = elapsed / 1000
            parts.append(f"elapsed={seconds:.1f}s")
        else:
            parts.append(f"elapsed={round(elapsed)}ms")
    parts.append(f"query={config.query_mode}")
    summary = result.get("summary")
    if summary and isinstance(summary, str) and len(summary) > 0:
        parts.append(f"summary={len(summary)} chars")
    return " ".join(parts)


def build_persisted_debug_summary(result: dict[str, Any]) -> str | None:
    if result.get("status") == "timeout_partial":
        summary = result.get("summary", "")
        return f"timeout_partial: {len(summary)} chars recovered (not persisted)"
    return result.get("summary")


def sanitize_debug_text(text: str) -> str:
    sanitized: list[str] = []
    for ch in text:
        code = ord(ch)
        is_control = (0x00 <= code <= 0x1F) or (0x7F <= code <= 0x9F)
        if not is_control:
            sanitized.append(ch)
    return " ".join("".join(sanitized).split())


def build_plugin_debug_line(
    summary: str | None = None,
    search_debug: Any | None = None,
) -> str | None:
    cleaned = sanitize_debug_text(summary or "")
    warning = sanitize_debug_text(search_debug.get("warning", "") if search_debug else "")
    action = sanitize_debug_text(search_debug.get("action", "") if search_debug else "")
    error = sanitize_debug_text(search_debug.get("error", "") if search_debug else "")
    debug_parts: list[str] = []
    backend = sanitize_debug_text(search_debug.get("backend", "") if search_debug else "")
    if backend:
        debug_parts.append(f"backend={backend}")
    configured_mode = sanitize_debug_text(search_debug.get("configuredMode", "") if search_debug else "")
    if configured_mode:
        debug_parts.append(f"configuredMode={configured_mode}")
    effective_mode = sanitize_debug_text(search_debug.get("effectiveMode", "") if search_debug else "")
    if effective_mode:
        debug_parts.append(f"effectiveMode={effective_mode}")
    fallback = sanitize_debug_text(search_debug.get("fallback", "") if search_debug else "")
    if fallback:
        debug_parts.append(f"fallback={fallback}")
    if search_debug:
        search_ms = search_debug.get("searchMs")
        if isinstance(search_ms, (int, float)):
            debug_parts.append(f"searchMs={max(0, round(search_ms))}")
        hits = search_debug.get("hits")
        if isinstance(hits, (int, float)):
            debug_parts.append(f"hits={max(0, int(hits))}")
    prefix = " ".join(debug_parts)
    warning_action = ""
    if warning and action and not cleaned:
        warning_action = f"{warning} {action}"
    elif warning or (action and not cleaned):
        parts = [warning, action if action and not cleaned else ""]
        warning_action = " | ".join(p for p in parts if p)
    messages = " | ".join(
        dict.fromkeys([v for v in [warning_action, cleaned] if v])
    )
    trailing = messages
    if prefix and trailing:
        return f"🔎 Active Memory Debug: {prefix} | {trailing}"
    if prefix:
        return f"🔎 Active Memory Debug: {prefix}"
    if messages:
        return f"🔎 Active Memory Debug: {messages}"
    if warning:
        return f"🔎 Active Memory Debug: {warning}"
    if cleaned:
        return f"🔎 Active Memory Debug: {cleaned}"
    if error:
        return f"🔎 Active Memory Debug: {error}"
    return None