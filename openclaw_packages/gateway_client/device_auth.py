from __future__ import annotations

from typing import Optional


def normalize_device_metadata_for_auth(value: Optional[str]) -> str:
    if not isinstance(value, str):
        return ""
    trimmed = value.strip()
    if not trimmed:
        return ""
    result = []
    for char in trimmed:
        if "A" <= char <= "Z":
            result.append(chr(ord(char) + 32))
        else:
            result.append(char)
    return "".join(result)


def build_device_auth_payload(
    *,
    device_id: str,
    client_id: str,
    client_mode: str,
    role: str,
    scopes: list[str],
    signed_at_ms: int,
    token: Optional[str] = None,
    nonce: str,
) -> str:
    scopes_str = ",".join(scopes)
    token_str = token if token is not None else ""
    return "|".join([
        "v2",
        device_id,
        client_id,
        client_mode,
        role,
        scopes_str,
        str(signed_at_ms),
        token_str,
        nonce,
    ])


def build_device_auth_payload_v3(
    *,
    device_id: str,
    client_id: str,
    client_mode: str,
    role: str,
    scopes: list[str],
    signed_at_ms: int,
    token: Optional[str] = None,
    nonce: str,
    platform: Optional[str] = None,
    device_family: Optional[str] = None,
) -> str:
    scopes_str = ",".join(scopes)
    token_str = token if token is not None else ""
    platform_normalized = normalize_device_metadata_for_auth(platform)
    device_family_normalized = normalize_device_metadata_for_auth(device_family)
    return "|".join([
        "v3",
        device_id,
        client_id,
        client_mode,
        role,
        scopes_str,
        str(signed_at_ms),
        token_str,
        nonce,
        platform_normalized,
        device_family_normalized,
    ])
