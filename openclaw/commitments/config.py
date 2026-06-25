"""Resolves commitment runtime configuration from agent and user settings."""

from __future__ import annotations

from typing import Any, TypedDict

DEFAULT_COMMITMENT_EXTRACTION_DEBOUNCE_MS = 15_000
DEFAULT_COMMITMENT_BATCH_MAX_ITEMS = 8
DEFAULT_COMMITMENT_EXTRACTION_QUEUE_MAX_ITEMS = 64
DEFAULT_COMMITMENT_CONFIDENCE_THRESHOLD = 0.72
DEFAULT_COMMITMENT_CARE_CONFIDENCE_THRESHOLD = 0.86
DEFAULT_COMMITMENT_EXTRACTION_TIMEOUT_SECONDS = 45
DEFAULT_COMMITMENT_MAX_PER_HEARTBEAT = 3
DEFAULT_COMMITMENT_EXPIRE_AFTER_HOURS = 72
DEFAULT_COMMITMENT_MAX_PER_DAY = 3


class ExtractionConfig(TypedDict):
    debounceMs: int
    batchMaxItems: int
    queueMaxItems: int
    confidenceThreshold: float
    careConfidenceThreshold: float
    timeoutSeconds: int


class ResolvedCommitmentsConfig(TypedDict):
    enabled: bool
    maxPerDay: int
    extraction: ExtractionConfig


def _positive_int(value: Any, fallback: int) -> int:
    if isinstance(value, (int, float)) and value == value and value > 0:
        return int(value)
    return fallback


def resolve_commitments_config(cfg: dict[str, Any] | None = None) -> ResolvedCommitmentsConfig:
    """Resolve commitment extraction config with conservative defaults."""
    raw = (cfg or {}).get("commitments") if cfg else None
    raw = raw if isinstance(raw, dict) else {}

    return ResolvedCommitmentsConfig(
        enabled=raw.get("enabled") is True,
        maxPerDay=_positive_int(raw.get("maxPerDay"), DEFAULT_COMMITMENT_MAX_PER_DAY),
        extraction=ExtractionConfig(
            debounceMs=DEFAULT_COMMITMENT_EXTRACTION_DEBOUNCE_MS,
            batchMaxItems=DEFAULT_COMMITMENT_BATCH_MAX_ITEMS,
            queueMaxItems=DEFAULT_COMMITMENT_EXTRACTION_QUEUE_MAX_ITEMS,
            confidenceThreshold=DEFAULT_COMMITMENT_CONFIDENCE_THRESHOLD,
            careConfidenceThreshold=DEFAULT_COMMITMENT_CARE_CONFIDENCE_THRESHOLD,
            timeoutSeconds=DEFAULT_COMMITMENT_EXTRACTION_TIMEOUT_SECONDS,
        ),
    )


def resolve_commitment_timezone(cfg: dict[str, Any] | None = None) -> str:
    """Resolve the timezone used when interpreting inferred commitment dates."""
    agents = (cfg or {}).get("agents", {}) if cfg else {}
    defaults = agents.get("defaults", {}) if isinstance(agents, dict) else {}
    tz = defaults.get("userTimezone", "") if isinstance(defaults, dict) else ""
    result = tz.strip() if isinstance(tz, str) else ""
    return result or "UTC"
