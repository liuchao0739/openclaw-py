"""Provider-owned error-pattern dispatch plus legacy fallback patterns."""

from __future__ import annotations

import re
from typing import Any, TypedDict

from openclaw.agents.embedded_agent_helpers.types import FailoverReason

PROVIDER_CONTEXT_OVERFLOW_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\binput token count exceeds the maximum number of input tokens\b",
        r"\binput is too long for this model\b",
        r"\binput exceeds the maximum number of tokens\b",
        r"\bollama error:\s*context length exceeded(?:,\s*too many tokens)?\b",
        r"\btotal tokens?.*exceeds? (?:the )?(?:model(?:'s)? )?(?:max|maximum|limit)",
        r"\b(?:request|prompt) \(\d[\d,]*\s*tokens?\) exceeds (?:the )?available context size\b",
        r"\binput (?:is )?too long for (?:the )?model\b",
    )
)

PROVIDER_SPECIFIC_PATTERNS: list[tuple[re.Pattern[str], FailoverReason]] = [
    (re.compile(r"\bthrottlingexception\b", re.I), "rate_limit"),
    (re.compile(r"\bconcurrency limit(?: has been)? reached\b", re.I), "rate_limit"),
    (re.compile(r"\bworkers_ai\b.*\bquota limit exceeded\b", re.I), "rate_limit"),
    (re.compile(r"\bmodelnotreadyexception\b", re.I), "overloaded"),
    (re.compile(r"model(?:_is)?_deactivated|model has been deactivated", re.I), "model_not_found"),
]

PROVIDER_CONTEXT_OVERFLOW_SIGNAL_RE = re.compile(
    r"\b(?:context|window|prompt|token|tokens|input|request|model)\b",
    re.I,
)
PROVIDER_CONTEXT_OVERFLOW_ACTION_RE = re.compile(
    r"\b(?:too\s+(?:large|long|many)|exceed(?:s|ed|ing)?|overflow|limit|maximum|max)\b",
    re.I,
)


class ProviderSpecificErrorContext(TypedDict, total=False):
    provider: str
    modelId: str
    errorMessage: str
    status: int
    code: str
    errorType: str


def _normalize_context(input_: str | ProviderSpecificErrorContext) -> ProviderSpecificErrorContext:
    if isinstance(input_, str):
        return {"errorMessage": input_}
    return input_


def _looks_like_overflow_candidate(error_message: str) -> bool:
    return bool(
        PROVIDER_CONTEXT_OVERFLOW_SIGNAL_RE.search(error_message)
        and PROVIDER_CONTEXT_OVERFLOW_ACTION_RE.search(error_message)
    )


def matches_provider_context_overflow(error_message: str) -> bool:
    if not _looks_like_overflow_candidate(error_message):
        return False
    return any(p.search(error_message) for p in PROVIDER_CONTEXT_OVERFLOW_PATTERNS)


def classify_provider_plugin_error(
    input_: str | ProviderSpecificErrorContext,
) -> FailoverReason | None:
    del input_
    return None


def classify_provider_specific_error(
    input_: str | ProviderSpecificErrorContext,
    *,
    include_plugin_hooks: bool = True,
) -> FailoverReason | None:
    context = _normalize_context(input_)
    msg = context.get("errorMessage", "")
    if include_plugin_hooks:
        plugin_reason = classify_provider_plugin_error(context)
        if plugin_reason:
            return plugin_reason
    for pattern, reason in PROVIDER_SPECIFIC_PATTERNS:
        if pattern.search(msg):
            return reason
    return None