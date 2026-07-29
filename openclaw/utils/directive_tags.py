from __future__ import annotations

import re

from openclaw.packages.normalization_core import normalize_optional_string

AUDIO_TAG_RE = re.compile(r"\[\[\s*audio_as_voice\s*\]\]", re.IGNORECASE)
REPLY_TAG_RE = re.compile(
    r"\[\[\s*(?:reply_to_current|reply_to\s*:\s*([^\]\n]+))\s*\]\]", re.IGNORECASE
)
INLINE_DIRECTIVE_TAG_WITH_PADDING_RE = re.compile(
    r"\s*(?:\[\[\s*audio_as_voice\s*\]\]|\[\[\s*(?:reply_to_current|reply_to\s*:\s*[^\]\n]+)\s*\]\])\s*",
    re.IGNORECASE,
)
MAX_REPLY_DIRECTIVE_ID_LENGTH = 256

BLOCK_SENTINEL_SEED = "\uE000"


def _replacement_preserves_word_boundary(source: str, offset: int, length: int) -> str:
    before = source[offset - 1] if offset > 0 else None
    after = source[offset + length] if offset + length < len(source) else None
    if before and after and not re.match(r"\s", before) and not re.match(r"\s", after):
        return " "
    return ""


def _create_block_sentinel(text: str) -> str:
    sentinel = BLOCK_SENTINEL_SEED
    while sentinel in text:
        sentinel += BLOCK_SENTINEL_SEED
    return sentinel


def _normalize_directive_whitespace(text: str) -> str:
    block_sentinel = _create_block_sentinel(text)
    block_placeholder_re = re.compile(f"{block_sentinel}(\\d+){block_sentinel}")
    blocks: list[str] = []

    def _stash_block(m: re.Match) -> str:
        blocks.append(m.group(0))
        return f"{block_sentinel}{len(blocks) - 1}{block_sentinel}"

    masked = re.sub(
        r"(`{3,}|~{3,})[^\n]*\n[\s\S]*?\n\1[^\n]*|(?:(?:^|\n)(?:    |\t)[^\n]*)+",
        _stash_block,
        text,
        flags=re.MULTILINE,
    )
    normalized = masked
    normalized = re.sub(r"\r\n", "\n", normalized)
    normalized = re.sub(r"([^\s])[ \t]{2,}([^\s])", r"\1 \2", normalized)
    normalized = re.sub(r"^\n+", "", normalized)
    normalized = re.sub(r"^[ \t](?=\S)", "", normalized, flags=re.MULTILINE)
    normalized = re.sub(r"[ \t]+\n", "\n", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    normalized = normalized.rstrip()
    return block_placeholder_re.sub(lambda m: blocks[int(m.group(1))], normalized)


def strip_inline_directive_tags_for_display(text: str) -> dict:
    if not text:
        return {"text": text, "changed": False}
    without_audio = AUDIO_TAG_RE.sub("", text)
    stripped = REPLY_TAG_RE.sub("", without_audio)
    return {"text": stripped, "changed": stripped != text}


def _strip_unsafe_reply_directive_chars(value: str) -> str:
    chars: list[str] = []
    for ch in value:
        code = ord(ch)
        if (0 <= code <= 31) or code == 127 or ch == "[" or ch == "]":
            continue
        chars.append(ch)
    return "".join(chars)


def sanitize_reply_directive_id(raw_reply_to_id: str | None = None) -> str | None:
    trimmed = (raw_reply_to_id or "").strip() if raw_reply_to_id else None
    if not trimmed:
        return None
    sanitized = _strip_unsafe_reply_directive_chars(trimmed).strip()
    if not sanitized:
        return None
    if len(sanitized) > MAX_REPLY_DIRECTIVE_ID_LENGTH:
        return sanitized[:MAX_REPLY_DIRECTIVE_ID_LENGTH]
    return sanitized


def strip_inline_directive_tags_for_delivery(text: str) -> dict:
    if not text:
        return {"text": text, "changed": False}
    stripped = INLINE_DIRECTIVE_TAG_WITH_PADDING_RE.sub(" ", text)
    changed = stripped != text
    return {"text": stripped.strip() if changed else text, "changed": changed}


def _is_message_text_part(part: object) -> bool:
    if not part or not isinstance(part, dict):
        return False
    return part.get("type") == "text" and isinstance(part.get("text"), str)


def strip_inline_directive_tags_from_message_for_display(message: dict | None) -> dict | None:
    if not message:
        return message
    content = message.get("content")
    if not isinstance(content, list):
        return message
    cleaned: list | None = None
    for i in range(len(content)):
        part = content[i]
        next_part: object = part
        if part and isinstance(part, dict) and _is_message_text_part(part):
            stripped = strip_inline_directive_tags_for_display(part["text"])
            if stripped["changed"]:
                next_part = {**part, "text": stripped["text"]}
        if next_part is part:
            if cleaned is not None:
                cleaned.append(part)
            continue
        if cleaned is None:
            cleaned = content[:i]
        cleaned.append(next_part)
    if cleaned is None:
        return message
    return {**message, "content": cleaned}


def parse_inline_directives(text: str | None = None, options: dict | None = None) -> dict:
    opts = options or {}
    current_message_id = opts.get("currentMessageId")
    strip_audio_tag = opts.get("stripAudioTag", True)
    strip_reply_tags = opts.get("stripReplyTags", True)
    if not text:
        return {
            "text": "",
            "audioAsVoice": False,
            "replyToCurrent": False,
            "hasAudioTag": False,
            "hasReplyTag": False,
        }
    if "[[" not in text:
        return {
            "text": _normalize_directive_whitespace(text),
            "audioAsVoice": False,
            "replyToCurrent": False,
            "hasAudioTag": False,
            "hasReplyTag": False,
        }

    cleaned = text
    audio_as_voice = False
    has_audio_tag = False
    has_reply_tag = False
    saw_current = False
    last_explicit_id: str | None = None

    def _audio_replacer(m: re.Match) -> str:
        nonlocal audio_as_voice, has_audio_tag
        audio_as_voice = True
        has_audio_tag = True
        if strip_audio_tag:
            return _replacement_preserves_word_boundary(m.string, m.start(), m.end() - m.start())
        return m.group(0)

    def _reply_replacer(m: re.Match) -> str:
        nonlocal has_reply_tag, saw_current, last_explicit_id
        has_reply_tag = True
        id_raw = m.group(1)
        if id_raw is None:
            saw_current = True
        else:
            id_val = id_raw.strip()
            if id_val:
                last_explicit_id = id_val
        if strip_reply_tags:
            return _replacement_preserves_word_boundary(m.string, m.start(), m.end() - m.start())
        return m.group(0)

    cleaned = AUDIO_TAG_RE.sub(_audio_replacer, cleaned)
    cleaned = REPLY_TAG_RE.sub(_reply_replacer, cleaned)
    cleaned = _normalize_directive_whitespace(cleaned)

    reply_to_id = last_explicit_id or (
        normalize_optional_string(current_message_id) if saw_current else None
    )

    return {
        "text": cleaned,
        "audioAsVoice": audio_as_voice,
        "replyToId": reply_to_id,
        "replyToExplicitId": last_explicit_id,
        "replyToCurrent": saw_current,
        "hasAudioTag": has_audio_tag,
        "hasReplyTag": has_reply_tag,
    }
