"""`/model` directive parser for auto-reply messages."""

from __future__ import annotations

import re
from typing import Any


def _split_trailing_auth_profile(model_ref: str) -> dict[str, str | None]:
    """Split a model reference into model and optional auth profile."""
    # Check for @profile suffix
    at_index = model_ref.rfind("@")
    if at_index > 0:
        model = model_ref[:at_index]
        profile = model_ref[at_index + 1:]
        if model and profile:
            return {"model": model, "profile": profile}
    return {"model": model_ref, "profile": None}


def extract_model_directive(
    body: str | None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract and remove a /model directive, including optional auth profile/runtime hints."""
    if not body:
        return {"cleaned": "", "hasDirective": False}

    # Match /model with optional model ref and optional --runtime flag
    model_match = re.search(
        r"(?:^|\s)/model(?=$|\s|:)\s*:?\s*([A-Za-z0-9_.:@-]+(?:/[A-Za-z0-9_.:@-]+)*)?"
        r"(?:\s+(?:--runtime|runtime=|harness=)\s*([A-Za-z0-9_.:-]+))?",
        body,
        re.IGNORECASE,
    )

    match = model_match
    raw = model_match.group(1).strip() if model_match and model_match.group(1) else None
    raw_runtime = model_match.group(2).strip() if model_match and model_match.group(2) else None

    # Check aliases if no direct match
    if not match and options and options.get("aliases"):
        for alias in options["aliases"]:
            alias_match = re.search(
                rf"(?:^|\s)/{re.escape(alias)}(?=$|\s|:)(?:\s*:\s*)?",
                body,
                re.IGNORECASE,
            )
            if alias_match:
                match = alias_match
                raw = alias.strip()
                break

    raw_model = raw
    raw_profile: str | None = None
    if raw:
        split = _split_trailing_auth_profile(raw)
        raw_model = split["model"]
        raw_profile = split["profile"]

    if match:
        cleaned = re.sub(r"\s+", " ", body.replace(match.group(0), " ")).strip()
    else:
        cleaned = body.strip()

    return {
        "cleaned": cleaned,
        "rawModel": raw_model,
        "rawProfile": raw_profile,
        "rawRuntime": raw_runtime,
        "hasDirective": bool(match),
    }
