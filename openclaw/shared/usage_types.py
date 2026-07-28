"""Usage types define shared usage accounting structures for sessions and runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SessionUsageEntryOrigin:
    label: str | None = None
    provider: str | None = None
    surface: str | None = None
    chat_type: str | None = None
    from_field: str | None = None
    to: str | None = None
    account_id: str | None = None
    thread_id: str | int | None = None


@dataclass
class SessionUsageEntry:
    key: str
    label: str | None = None
    session_id: str | None = None
    scope: str | None = None
    session_family_key: str | None = None
    current_session_id: str | None = None
    included_session_ids: list[str] | None = None
    historical_instance_count: int | None = None
    updated_at: int | None = None
    agent_id: str | None = None
    channel: str | None = None
    chat_type: str | None = None
    origin: SessionUsageEntryOrigin | None = None
    model_override: str | None = None
    provider_override: str | None = None
    model_provider: str | None = None
    model: str | None = None
    usage: Any = None
    context_weight: Any = None


@dataclass
class SessionsUsageAggregates:
    messages: Any = None
    tools: Any = None
    by_model: list[Any] = field(default_factory=list)
    by_provider: list[Any] = field(default_factory=list)
    by_agent: list[dict[str, Any]] = field(default_factory=list)
    by_channel: list[dict[str, Any]] = field(default_factory=list)
    latency: Any = None
    daily_latency: list[Any] = field(default_factory=list)
    model_daily: list[Any] = field(default_factory=list)
    daily: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SessionsUsageResult:
    updated_at: int
    start_date: str
    end_date: str
    sessions: list[SessionUsageEntry] = field(default_factory=list)
    totals: Any = None
    aggregates: SessionsUsageAggregates | None = None
    cache_status: Any = None
