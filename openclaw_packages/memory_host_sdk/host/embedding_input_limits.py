from __future__ import annotations

from typing import Optional

from .embedding_inputs import EmbeddingInput


def estimate_utf8_bytes(text: str) -> int:
    if not text:
        return 0
    return len(text.encode("utf-8"))


def estimate_structured_embedding_input_bytes(input_data: EmbeddingInput) -> int:
    if not input_data.get("parts"):
        return estimate_utf8_bytes(input_data.get("text", ""))
    total = 0
    for part in input_data["parts"]:
        if part.get("type") == "text":
            total += estimate_utf8_bytes(part.get("text", ""))
        else:
            total += estimate_utf8_bytes(part.get("mimeType", ""))
            total += estimate_utf8_bytes(part.get("data", ""))
    return total


def split_text_to_utf8_byte_limit(text: str, max_utf8_bytes: int) -> list:
    if max_utf8_bytes <= 0:
        return [text]
    if estimate_utf8_bytes(text) <= max_utf8_bytes:
        return [text]

    parts = []
    cursor = 0
    while cursor < len(text):
        low = cursor + 1
        high = min(len(text), cursor + max_utf8_bytes)
        best = cursor

        while low <= high:
            mid = (low + high) // 2
            byte_count = estimate_utf8_bytes(text[cursor:mid])
            if byte_count <= max_utf8_bytes:
                best = mid
                low = mid + 1
            else:
                high = mid - 1

        if best <= cursor:
            best = min(len(text), cursor + 1)

        if best < len(text) and best > cursor:
            code_at_best = ord(text[best - 1])
            if 0xd800 <= code_at_best <= 0xdbff and best < len(text):
                code_at_next = ord(text[best])
                if 0xdc00 <= code_at_next <= 0xdfff:
                    best -= 1

        part = text[cursor:best]
        if not part:
            break
        parts.append(part)
        cursor = best

    return parts
