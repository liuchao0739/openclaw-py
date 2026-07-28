from __future__ import annotations

import secrets
import time

_last_timestamp = float("-inf")
_sequence = 0


def _fill_random_bytes(length: int) -> bytearray:
    return bytearray(secrets.token_bytes(length))


def uuidv7() -> str:
    global _last_timestamp, _sequence

    random_bytes = _fill_random_bytes(16)
    timestamp = int(time.time() * 1000)

    if timestamp > _last_timestamp:
        _sequence = (
            random_bytes[6] * 0x1000000
            + random_bytes[7] * 0x10000
            + random_bytes[8] * 0x100
            + random_bytes[9]
        )
        _last_timestamp = timestamp
    else:
        _sequence = (_sequence + 1) & 0xFFFFFFFF
        if _sequence == 0:
            _last_timestamp += 1

    ts = int(_last_timestamp)
    bytes_arr = bytearray(16)
    bytes_arr[0] = (ts // 0x10000000000) & 0xFF
    bytes_arr[1] = (ts // 0x100000000) & 0xFF
    bytes_arr[2] = (ts // 0x1000000) & 0xFF
    bytes_arr[3] = (ts // 0x10000) & 0xFF
    bytes_arr[4] = (ts // 0x100) & 0xFF
    bytes_arr[5] = ts & 0xFF
    bytes_arr[6] = 0x70 | ((_sequence >> 28) & 0x0F)
    bytes_arr[7] = (_sequence >> 20) & 0xFF
    bytes_arr[8] = 0x80 | ((_sequence >> 14) & 0x3F)
    bytes_arr[9] = (_sequence >> 6) & 0xFF
    bytes_arr[10] = ((_sequence & 0x3F) << 2) | (random_bytes[10] & 0x03)
    bytes_arr[11] = random_bytes[11]
    bytes_arr[12] = random_bytes[12]
    bytes_arr[13] = random_bytes[13]
    bytes_arr[14] = random_bytes[14]
    bytes_arr[15] = random_bytes[15]

    return _format_uuid(bytes_arr)


def _format_uuid(byte_arr: bytearray) -> str:
    hex_parts = [f"{b:02x}" for b in byte_arr]
    return (
        f"{''.join(hex_parts[0:4])}-"
        f"{''.join(hex_parts[4:6])}-"
        f"{''.join(hex_parts[6:8])}-"
        f"{''.join(hex_parts[8:10])}-"
        f"{''.join(hex_parts[10:16])}"
    )
