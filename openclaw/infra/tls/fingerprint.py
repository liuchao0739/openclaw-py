from __future__ import annotations

import hashlib
import os
import re
from typing import Any


def compute_file_sha256(file_path: str) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def compute_string_sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def compute_bytes_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fingerprint_cert(cert_path: str) -> str | None:
    try:
        with open(cert_path, "r") as f:
            content = f.read()
        return compute_string_sha256(content)
    except (OSError, IOError):
        return None


def normalize_fingerprint(input: str) -> str:
    trimmed = input.strip()
    without_prefix = re.sub(r"^sha-?256\s*:?\s*", "", trimmed, flags=re.IGNORECASE)
    hex_only = re.sub(r"[^a-fA-F0-9]", "", without_prefix)
    return hex_only.lower()
