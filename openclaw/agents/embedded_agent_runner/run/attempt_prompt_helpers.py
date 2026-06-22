"""Builds and repairs prompt inputs for embedded-agent attempts (core merge path)."""

from __future__ import annotations

import json
import re
from typing import Any

from openclaw.agents.embedded_agent_runner.run.params import EmbeddedRunTrigger

QUEUED_USER_MESSAGE_MARKER = (
    "[Queued user message that arrived while the previous turn was still active]"
)
MAX_STRUCTURED_MEDIA_REF_CHARS = 300
MAX_STRUCTURED_JSON_STRING_CHARS = 300
MAX_STRUCTURED_JSON_DEPTH = 4
MAX_STRUCTURED_JSON_ARRAY_ITEMS = 16
MAX_STRUCTURED_JSON_OBJECT_KEYS = 32

_prompt_build_drain_cache: dict[str, list[Any]] = {}
PROMPT_BUILD_DRAIN_CACHE_MAX = 256


def forget_prompt_build_drain_cache_for_run(run_id: str | None) -> None:
    if run_id:
        _prompt_build_drain_cache.pop(run_id, None)


def _summarize_structured_media_ref(label: str, value: object) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    data_uri = re.match(r"^data:([^;,]+)?(?:;[^,]*)?,", trimmed, re.I)
    if data_uri:
        mime = (data_uri.group(1) or "unknown").strip()
        return f"[{label}] inline data URI ({mime}, {len(trimmed)} chars)"
    if len(trimmed) > MAX_STRUCTURED_MEDIA_REF_CHARS:
        return (
            f"[{label}] {trimmed[:MAX_STRUCTURED_MEDIA_REF_CHARS]}... "
            f"({len(trimmed)} chars)"
        )
    return f"[{label}] {trimmed}"


def _summarize_structured_json_string(value: str) -> str:
    media = _summarize_structured_media_ref("value", value)
    if media and "inline data URI" in media:
        return media
    trimmed = value.strip()
    if len(trimmed) > MAX_STRUCTURED_JSON_STRING_CHARS:
        return f"{trimmed[:MAX_STRUCTURED_JSON_STRING_CHARS]}... ({len(trimmed)} chars)"
    return value


def _sanitize_structured_json_value(
    value: object,
    depth: int = 0,
    seen: set[int] | None = None,
) -> object:
    if isinstance(value, str):
        return _summarize_structured_json_string(value)
    if not value or not isinstance(value, (dict, list)):
        return value
    sid = id(value)
    if seen is None:
        seen = set()
    if sid in seen:
        return "[circular]"
    if depth >= MAX_STRUCTURED_JSON_DEPTH:
        return "[max depth]"
    seen.add(sid)
    if isinstance(value, list):
        limited = [
            _sanitize_structured_json_value(item, depth + 1, seen)
            for item in value[:MAX_STRUCTURED_JSON_ARRAY_ITEMS]
        ]
        if len(value) > MAX_STRUCTURED_JSON_ARRAY_ITEMS:
            limited.append(f"[{len(value) - MAX_STRUCTURED_JSON_ARRAY_ITEMS} more items]")
        seen.discard(sid)
        return limited
    out: dict[str, object] = {}
    copied = 0
    skipped = 0
    for key, val in value.items():
        if copied >= MAX_STRUCTURED_JSON_OBJECT_KEYS:
            skipped += 1
            continue
        out[key] = _sanitize_structured_json_value(val, depth + 1, seen)
        copied += 1
    if skipped > 0:
        out["__truncated"] = f"{skipped} more keys"
    seen.discard(sid)
    return out


def _stringify_structured_json_fallback(part: object) -> str | None:
    try:
        serialized = json.dumps(_sanitize_structured_json_value(part))
        if not serialized or serialized == "{}":
            return None
        without_inline = re.sub(
            r"data:[^\"'\\\s]+",
            lambda m: f"[inline data URI: {len(m.group(0))} chars]",
            serialized,
            flags=re.I,
        )
        if len(without_inline) > 1000:
            return f"{without_inline[:1000]}... ({len(without_inline)} chars)"
        return without_inline
    except (TypeError, ValueError):
        return None


def _stringify_structured_content_part(part: object) -> str | None:
    if not part or not isinstance(part, dict):
        return None
    if part.get("type") == "text":
        text = part.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
        return None
    if part.get("type") == "image_url":
        image_url = part.get("image_url")
        url = image_url if isinstance(image_url, str) else None
        if isinstance(image_url, dict):
            u = image_url.get("url")
            url = u if isinstance(u, str) else None
        return _summarize_structured_media_ref("image_url", url)
    if part.get("type") in ("image", "input_image"):
        return _summarize_structured_media_ref(
            str(part.get("type")),
            part.get("url") or part.get("source"),
        )
    block_type = part.get("type")
    if isinstance(block_type, str):
        for key in ("audio_url", "media_url", "url", "source"):
            ref = _summarize_structured_media_ref(block_type, part.get(key))
            if ref:
                return ref
    return _stringify_structured_json_fallback(part)


def extract_user_message_prompt_text(content: object) -> str | None:
    if isinstance(content, str):
        trimmed = content.strip()
        return trimmed or None
    if not isinstance(content, list):
        return None
    parts = []
    for part in content:
        text = _stringify_structured_content_part(part)
        if text:
            parts.append(text)
    joined = "\n".join(parts).strip()
    return joined or None


def prompt_already_includes_queued_user_message(prompt: str, orphan_text: str) -> bool:
    normalized_prompt = prompt.replace("\r\n", "\n")
    normalized_orphan = orphan_text.replace("\r\n", "\n").strip()
    if not normalized_orphan:
        return False
    queued_block_prefix = f"{QUEUED_USER_MESSAGE_MARKER}\n{normalized_orphan}"
    return (
        normalized_prompt == queued_block_prefix
        or normalized_prompt.startswith(f"{queued_block_prefix}\n")
        or f"\n{queued_block_prefix}\n" in normalized_prompt
        or f"\n{normalized_prompt}\n".find(f"\n{normalized_orphan}\n") >= 0
    )


def merge_orphaned_trailing_user_prompt(
    *,
    prompt: str,
    trigger: EmbeddedRunTrigger | None,
    leaf_message: dict[str, Any],
) -> dict[str, Any]:
    _ = trigger  # reserved for trigger-specific policy
    orphan_text = extract_user_message_prompt_text(leaf_message.get("content"))
    if not orphan_text:
        return {"prompt": prompt, "merged": False, "removeLeaf": True}
    if prompt_already_includes_queued_user_message(prompt, orphan_text):
        return {"prompt": prompt, "merged": False, "removeLeaf": True}
    return {
        "prompt": "\n".join([QUEUED_USER_MESSAGE_MARKER, orphan_text, "", prompt]),
        "merged": True,
        "removeLeaf": True,
    }