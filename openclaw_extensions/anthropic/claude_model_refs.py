from __future__ import annotations

import re
from typing import Any

from openclaw.packages.normalization_core import normalize_lowercase_string_or_empty

from .cli_constants import CLAUDE_CLI_BACKEND_ID, CLAUDE_CLI_MODEL_ALIASES

DEFAULT_CLAUDE_MODEL_BY_FAMILY: dict[str, str] = {
    "opus": "claude-opus-4-8",
    "sonnet": "claude-sonnet-4-6",
    "haiku": "claude-haiku-4-5",
}


def _split_trailing_model_auth_profile(raw: str) -> dict[str, str]:
    trimmed = raw.strip()
    if not trimmed:
        return {"model": ""}
    last_slash = trimmed.rfind("/")
    delimiter = trimmed.find("@", last_slash + 1)
    if delimiter <= 0:
        return {"model": trimmed}
    if re.match(r"^\d{8}(?:@|$)", trimmed[delimiter + 1:]):
        next_delimiter = trimmed.find("@", delimiter + 9)
        if next_delimiter < 0:
            return {"model": trimmed}
        delimiter = next_delimiter
    model = trimmed[:delimiter].strip()
    profile = trimmed[delimiter + 1:].strip()
    return {"model": model, "profile": profile} if model and profile else {"model": trimmed}


def _attach_model_auth_profile(model: str, profile: str | None = None) -> str:
    return f"{model}@{profile}" if profile else model


def _has_retired_version_prefix(normalized: str, prefix: str) -> bool:
    if normalized == prefix:
        return True
    if not normalized.startswith(prefix):
        return False
    next_char = normalized[len(prefix)]
    return next_char in ("-", ".", ":", "@")


def _has_any_retired_version_prefix(normalized: str, prefixes: list[str]) -> bool:
    return any(_has_retired_version_prefix(normalized, p) for p in prefixes)


def _parse_provider_model_ref(
    raw: str, default_provider: str
) -> dict[str, Any] | None:
    trimmed = raw.strip()
    if not trimmed:
        return None
    slash_index = trimmed.find("/")
    if slash_index <= 0:
        return {
            "provider": default_provider,
            "model": trimmed,
            "explicitProvider": False,
        }
    provider = trimmed[:slash_index].strip()
    model = trimmed[slash_index + 1:].strip()
    if not provider or not model:
        return None
    return {
        "provider": normalize_lowercase_string_or_empty(provider),
        "model": model,
        "explicitProvider": True,
    }


def _upgrade_old_claude_model_id(normalized: str) -> str | None:
    if normalized.startswith("claude-opus-4-8") or normalized.startswith("claude-opus-4.8"):
        return None
    if normalized.startswith("claude-opus-4-7") or normalized.startswith("claude-opus-4.7"):
        return None
    if normalized.startswith("claude-opus-4-6") or normalized.startswith("claude-opus-4.6"):
        return None
    if normalized.startswith("claude-sonnet-4-6") or normalized.startswith("claude-sonnet-4.6"):
        return None
    if normalized.startswith("claude-haiku-4-5") or normalized.startswith("claude-haiku-4.5"):
        return None
    if normalized == "claude-opus-4" or _has_any_retired_version_prefix(
        normalized,
        [
            "claude-opus-4-7",
            "claude-opus-4.7",
            "claude-opus-4-5",
            "claude-opus-4.5",
            "claude-opus-4-1",
            "claude-opus-4.1",
            "claude-opus-4-0",
            "claude-opus-4.0",
        ],
    ) or re.match(r"^claude-opus-4-20\d{6}", normalized):
        return "claude-opus-4-8"
    if normalized == "claude-sonnet-4" or _has_any_retired_version_prefix(
        normalized,
        [
            "claude-sonnet-4-5",
            "claude-sonnet-4.5",
            "claude-sonnet-4-1",
            "claude-sonnet-4.1",
            "claude-sonnet-4-0",
            "claude-sonnet-4.0",
        ],
    ) or re.match(r"^claude-sonnet-4-20\d{6}", normalized):
        return "claude-sonnet-4-6"
    if normalized.startswith("claude-3") and "opus" in normalized:
        return "claude-opus-4-8"
    if normalized.startswith("claude-3") and (
        "sonnet" in normalized or "haiku" in normalized
    ):
        return "claude-sonnet-4-6"
    if normalized in (
        "opus-4.5",
        "opus-4.1",
        "opus-4",
        "opus-3",
    ):
        return "claude-opus-4-8"
    if normalized in (
        "sonnet-4.5",
        "sonnet-4.1",
        "sonnet-4.0",
        "sonnet-4",
        "sonnet-3.7",
        "sonnet-3.5",
        "sonnet-3",
        "haiku-3.5",
        "haiku-3",
    ):
        return "claude-sonnet-4-6"
    return None


def _canonicalize_known_claude_cli_model_id(model_id: str) -> str | None:
    split = _split_trailing_model_auth_profile(model_id)
    trimmed = split["model"].strip()
    normalized = normalize_lowercase_string_or_empty(trimmed)
    if not normalized:
        return None
    upgraded = _upgrade_old_claude_model_id(normalized)
    if upgraded:
        return _attach_model_auth_profile(upgraded, split.get("profile"))
    if normalized.startswith("claude-"):
        return _attach_model_auth_profile(trimmed, split.get("profile"))
    default_model = DEFAULT_CLAUDE_MODEL_BY_FAMILY.get(normalized)
    if default_model:
        return _attach_model_auth_profile(default_model, split.get("profile"))
    aliased_model = CLAUDE_CLI_MODEL_ALIASES.get(normalized)
    if aliased_model and aliased_model.startswith("claude-"):
        return _attach_model_auth_profile(aliased_model, split.get("profile"))
    return None


def resolve_claude_cli_anthropic_model_refs(
    raw: str,
) -> dict[str, Any] | None:
    parsed = _parse_provider_model_ref(raw, "anthropic")
    if not parsed:
        return None
    if parsed["provider"] not in ("anthropic", CLAUDE_CLI_BACKEND_ID):
        return None

    selected_ref = f"anthropic/{parsed['model']}"
    runtime_refs: set[str] = {selected_ref}
    canonical_model_id = _canonicalize_known_claude_cli_model_id(parsed["model"])
    if not parsed.get("explicitProvider") and not canonical_model_id:
        return None
    rewrite_ref = None
    if canonical_model_id or parsed["provider"] == CLAUDE_CLI_BACKEND_ID:
        rewrite_ref = f"anthropic/{canonical_model_id or parsed['model']}"
        runtime_refs.add(rewrite_ref)

    result: dict[str, Any] = {
        "selectedRef": selected_ref,
        "runtimeRefs": list(runtime_refs),
    }
    if rewrite_ref:
        result["rewriteRef"] = rewrite_ref
    return result


def resolve_known_anthropic_model_ref(raw: str | None = None) -> str | None:
    if not raw:
        return None
    trimmed = raw.strip()
    if not trimmed:
        return None
    refs = resolve_claude_cli_anthropic_model_refs(trimmed)
    if refs and refs.get("rewriteRef"):
        return refs["rewriteRef"]
    return trimmed