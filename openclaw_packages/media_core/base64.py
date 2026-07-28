from __future__ import annotations


def estimate_base64_decoded_bytes(base64: str) -> int:
    effective_len = 0
    i = 0
    n = len(base64)
    while i < n:
        code = ord(base64[i])
        if code <= 0x20:
            i += 1
            continue
        effective_len += 1
        i += 1

    if effective_len == 0:
        return 0

    padding = 0
    end = n - 1
    while end >= 0 and ord(base64[end]) <= 0x20:
        end -= 1
    if end >= 0 and base64[end] == "=":
        padding = 1
        end -= 1
        while end >= 0 and ord(base64[end]) <= 0x20:
            end -= 1
        if end >= 0 and base64[end] == "=":
            padding = 2

    estimated = (effective_len * 3) // 4 - padding
    return max(0, estimated)


def _is_base64_data_char(code: int) -> bool:
    return (
        (0x41 <= code <= 0x5A)
        or (0x61 <= code <= 0x7A)
        or (0x30 <= code <= 0x39)
        or code == 0x2B
        or code == 0x2F
    )


def canonicalize_base64(base64: str) -> str | None:
    cleaned = ""
    padding = 0
    saw_padding = False
    i = 0
    n = len(base64)
    while i < n:
        code = ord(base64[i])
        if code <= 0x20:
            i += 1
            continue
        if code == 0x3D:
            padding += 1
            if padding > 2:
                return None
            saw_padding = True
            cleaned += "="
            i += 1
            continue
        if saw_padding or not _is_base64_data_char(code):
            return None
        cleaned += base64[i]
        i += 1
    if not cleaned:
        return None
    remainder = len(cleaned) % 4
    if remainder != 0:
        if saw_padding or remainder == 1:
            return None
        cleaned += "=" * (4 - remainder)
    return cleaned
