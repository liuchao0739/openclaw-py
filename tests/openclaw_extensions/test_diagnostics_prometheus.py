"""Tests for the diagnostics-prometheus extension service behavior."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from openclaw.plugin_sdk import diagnostic_runtime, security_runtime
from openclaw_extensions.diagnostics_prometheus import api, index
from openclaw_extensions.diagnostics_prometheus.src.service import (
    create_diagnostics_prometheus_exporter,
    test_api,
)

TRUSTED: dict[str, bool] = {"trusted": True}
UNTRUSTED: dict[str, bool] = {"trusted": False}


def base_event() -> dict[str, Any]:
    return {"seq": 1, "ts": 1700000000000}


def test_api_reexports_plugin_contract() -> None:
    assert api.empty_plugin_config_schema is not None
    assert api.OpenClawPluginApi is not None
    assert api.OpenClawPluginHttpRouteHandler is not None
    assert api.OpenClawPluginService is not None
    assert api.OpenClawPluginServiceContext is not None
    assert (
        api.is_internal_diagnostic_event_metadata
        is diagnostic_runtime.is_internal_diagnostic_event_metadata
    )
    assert api.redact_sensitive_text is security_runtime.redact_sensitive_text


def test_index_default_entry_metadata() -> None:
    entry = index.default
    assert entry.id == "diagnostics-prometheus"
    assert entry.name == "Diagnostics Prometheus"
    assert "Prometheus" in entry.description
    assert callable(entry.register)
    assert entry.config_schema is not None
    assert callable(entry.config_schema["safeParse"])


def test_records_trusted_run_metrics_without_raw_diagnostic_identifiers() -> None:
    store = test_api["create_prometheus_metric_store"]()

    test_api["record_diagnostic_event"](
        store,
        {
            **base_event(),
            "type": "run.completed",
            "runId": "run-should-not-export",
            "sessionKey": "session-should-not-export",
            "provider": "openai",
            "model": "gpt-5.4",
            "channel": "discord",
            "trigger": "message",
            "durationMs": 1500,
            "outcome": "completed",
        },
        TRUSTED,
    )

    rendered = test_api["render_prometheus_metrics"](store)

    assert "# TYPE openclaw_run_completed_total counter" in rendered
    assert (
        'openclaw_run_completed_total{channel="discord",model="gpt-5.4",outcome="completed",provider="openai",trigger="message"} 1'
        in rendered
    )
    assert (
        'openclaw_run_duration_seconds_sum{channel="discord",model="gpt-5.4",outcome="completed",provider="openai",trigger="message"} 1.5'
        in rendered
    )
    assert "run-should-not-export" not in rendered
    assert "session-should-not-export" not in rendered


def test_records_hook_blocked_run_metrics_with_safe_blocker_originator_only() -> None:
    store = test_api["create_prometheus_metric_store"]()

    test_api["record_diagnostic_event"](
        store,
        {
            **base_event(),
            "type": "run.completed",
            "runId": "run-should-not-export",
            "sessionKey": "session-should-not-export",
            "provider": "openai",
            "model": "gpt-5.4",
            "channel": "slack",
            "trigger": "message",
            "durationMs": 250,
            "outcome": "blocked",
            "blockedBy": "policy-plugin",
        },
        TRUSTED,
    )

    rendered = test_api["render_prometheus_metrics"](store)

    assert (
        'openclaw_run_completed_total{blocked_by="policy-plugin",channel="slack",model="gpt-5.4",outcome="blocked",provider="openai",trigger="message"} 1'
        in rendered
    )
    assert "run-should-not-export" not in rendered
    assert "session-should-not-export" not in rendered
    assert "matched secret prompt" not in rendered


def test_drops_untrusted_plugin_emitted_diagnostic_events() -> None:
    store = test_api["create_prometheus_metric_store"]()

    test_api["record_diagnostic_event"](
        store,
        {
            **base_event(),
            "type": "model.call.completed",
            "runId": "run-1",
            "callId": "call-1",
            "provider": "openai",
            "model": "gpt-5.4",
            "durationMs": 10,
        },
        UNTRUSTED,
    )

    assert test_api["render_prometheus_metrics"](store) == ""


def test_drops_untrusted_events_that_spoof_gateway_stability_signals() -> None:
    store = test_api["create_prometheus_metric_store"]()

    for event in (
        {
            **base_event(),
            "type": "webhook.received",
            "channel": "telegram",
            "updateType": "message",
        },
        {
            **base_event(),
            "type": "payload.large",
            "surface": "gateway.frame",
            "action": "rejected",
            "bytes": 2048,
        },
        {
            **base_event(),
            "type": "session.stuck",
            "state": "processing",
            "ageMs": 12_000,
            "classification": "stale_session_state",
        },
    ):
        test_api["record_diagnostic_event"](store, event, UNTRUSTED)

    assert test_api["render_prometheus_metrics"](store) == ""


def test_records_sanitized_async_diagnostic_queue_drop_summaries_from_core_diagnostics() -> None:
    store = test_api["create_prometheus_metric_store"]()

    test_api["record_diagnostic_event"](
        store,
        {
            **base_event(),
            "type": "diagnostic.async_queue.dropped",
            "droppedEvents": 3,
            "droppedTrustedEvents": 1,
            "droppedUntrustedEvents": 2,
            "queueLength": 0,
            "maxQueueLength": 10_000,
            "drainBatchSize": 100,
        },
        TRUSTED,
    )

    rendered = test_api["render_prometheus_metrics"](store)

    assert 'openclaw_diagnostic_async_queue_dropped_total{drop_class="total"} 3' in rendered
    assert 'openclaw_diagnostic_async_queue_dropped_total{drop_class="trusted"} 1' in rendered
    assert 'openclaw_diagnostic_async_queue_dropped_total{drop_class="untrusted"} 2' in rendered
    assert "openclaw_diagnostic_async_queue_length 0" in rendered


def test_redacts_and_bounds_label_values() -> None:
    store = test_api["create_prometheus_metric_store"]()

    test_api["record_diagnostic_event"](
        store,
        {
            **base_event(),
            "type": "tool.execution.error",
            "toolName": "shell\nbad",
            "durationMs": 25,
            "errorCategory": "Bearer sk-secret-token-value",
        },
        TRUSTED,
    )

    rendered = test_api["render_prometheus_metrics"](store)

    assert (
        'openclaw_tool_execution_total{error_category="other",outcome="error",params_kind="unknown",tool="tool",tool_owner="none",tool_source="core"} 1'
        in rendered
    )
    assert "Bearer" not in rendered
    assert "sk-secret" not in rendered


def test_records_operator_critical_diagnostic_signals_missing_from_generic_run_metrics() -> None:
    store = test_api["create_prometheus_metric_store"]()

    for event in (
        {
            **base_event(),
            "type": "tool.execution.blocked",
            "toolName": "browser",
            "toolSource": "mcp",
            "toolOwner": "browser-tools",
            "deniedReason": "tools.deny",
            "reason": "matched browser",
            "paramsSummary": {"kind": "object"},
        },
        {
            **base_event(),
            "type": "model.failover",
            "lane": "session:Agent:qa:otel-trace-smoke",
            "fromProvider": "anthropic",
            "fromModel": "claude-opus-4-6",
            "toProvider": "openai",
            "toModel": "gpt-5.4",
            "reason": "overloaded",
            "suspended": True,
        },
        {
            **base_event(),
            "type": "session.stuck",
            "sessionId": "session-should-not-export",
            "sessionKey": "key-should-not-export",
            "state": "processing",
            "ageMs": 12_000,
            "classification": "stale_session_state",
            "reason": "startup-sweep",
        },
        {
            **base_event(),
            "type": "payload.large",
            "surface": "gateway.frame",
            "action": "rejected",
            "bytes": 2048,
            "limitBytes": 1024,
            "channel": "web",
            "pluginId": "agent:qa:otel-trace-smoke",
            "reason": "body-too-large",
        },
    ):
        test_api["record_diagnostic_event"](store, event, TRUSTED)

    rendered = test_api["render_prometheus_metrics"](store)

    assert (
        'openclaw_tool_execution_blocked_total{denied_reason="tools.deny",params_kind="object",tool="browser",tool_owner="browser-tools",tool_source="mcp"} 1'
        in rendered
    )
    assert (
        'openclaw_model_failover_total{from_model="claude-opus-4-6",from_provider="anthropic",lane="session",reason="overloaded",suspended="true",to_model="gpt-5.4",to_provider="openai"} 1'
        in rendered
    )
    assert 'openclaw_session_stuck_total{reason="startup-sweep",state="processing"} 1' in rendered
    assert (
        'openclaw_session_stuck_age_seconds_sum{reason="startup-sweep",state="processing"} 12'
        in rendered
    )
    assert (
        'openclaw_payload_large_total{action="rejected",channel="web",plugin="none",reason="body-too-large",surface="gateway.frame"} 1'
        in rendered
    )
    assert (
        'openclaw_payload_large_bytes_sum{action="rejected",channel="web",plugin="none",reason="body-too-large",surface="gateway.frame"} 2048'
        in rendered
    )
    assert "session-should-not-export" not in rendered
    assert "key-should-not-export" not in rendered
    assert "Agent:qa:otel-trace-smoke" not in rendered


def test_records_webhook_ingress_and_liveness_warning_metrics() -> None:
    store = test_api["create_prometheus_metric_store"]()

    test_api["record_diagnostic_event"](
        store,
        {
            **base_event(),
            "type": "webhook.received",
            "channel": "telegram",
            "updateType": "message",
            "chatId": "chat-should-not-export",
        },
        TRUSTED,
    )
    test_api["record_diagnostic_event"](
        store,
        {
            **base_event(),
            "type": "webhook.processed",
            "channel": "telegram",
            "updateType": "message",
            "chatId": "chat-should-not-export",
            "durationMs": 250,
        },
        TRUSTED,
    )
    test_api["record_diagnostic_event"](
        store,
        {
            **base_event(),
            "type": "webhook.error",
            "channel": "telegram",
            "updateType": "message",
            "chatId": "chat-should-not-export",
            "error": "Bearer sk-secret",
        },
        TRUSTED,
    )
    test_api["record_diagnostic_event"](
        store,
        {
            **base_event(),
            "type": "diagnostic.liveness.warning",
            "reasons": ["event_loop_delay", "cpu"],
            "intervalMs": 30_000,
            "eventLoopDelayP99Ms": 250,
            "eventLoopDelayMaxMs": 900,
            "eventLoopUtilization": 0.95,
            "cpuCoreRatio": 1.4,
            "active": 2,
            "waiting": 1,
            "queued": 4,
        },
        TRUSTED,
    )

    rendered = test_api["render_prometheus_metrics"](store)

    assert 'openclaw_webhook_received_total{channel="telegram",webhook="message"} 1' in rendered
    assert 'openclaw_webhook_error_total{channel="telegram",webhook="message"} 1' in rendered
    assert (
        'openclaw_webhook_duration_seconds_sum{channel="telegram",webhook="message"} 0.25'
        in rendered
    )
    assert 'openclaw_liveness_warning_total{reason="event_loop_delay:cpu"} 1' in rendered
    assert 'openclaw_liveness_sessions{state="active"} 2' in rendered
    assert (
        'openclaw_liveness_event_loop_delay_p99_seconds_sum{reason="event_loop_delay:cpu"} 0.25'
        in rendered
    )
    assert 'openclaw_liveness_cpu_core_ratio_sum{reason="event_loop_delay:cpu"} 1.4' in rendered
    assert "chat-should-not-export" not in rendered
    assert "sk-secret" not in rendered


def test_drops_session_shaped_agent_labels() -> None:
    store = test_api["create_prometheus_metric_store"]()

    test_api["record_diagnostic_event"](
        store,
        {
            **base_event(),
            "type": "model.usage",
            "agentId": "Agent:qa:otel-trace-smoke",
            "provider": "openai",
            "model": "gpt-5.4",
            "usage": {"input": 12},
        },
        TRUSTED,
    )

    rendered = test_api["render_prometheus_metrics"](store)

    assert (
        'openclaw_model_tokens_total{agent="unknown",channel="unknown",model="gpt-5.4",provider="openai",token_type="input"} 12'
        in rendered
    )
    assert "Agent:qa:otel-trace-smoke" not in rendered


def test_drops_session_shaped_queue_lane_labels() -> None:
    store = test_api["create_prometheus_metric_store"]()

    test_api["record_diagnostic_event"](
        store,
        {
            **base_event(),
            "type": "queue.lane.enqueue",
            "lane": "session:Agent:qa:otel-trace-smoke",
            "queueSize": 2,
        },
        TRUSTED,
    )

    rendered = test_api["render_prometheus_metrics"](store)

    assert 'openclaw_queue_lane_size{lane="session"} 2' in rendered
    assert "Agent:qa:otel-trace-smoke" not in rendered


def test_keeps_only_the_bounded_prefix_from_scoped_queue_lane_labels() -> None:
    store = test_api["create_prometheus_metric_store"]()

    test_api["record_diagnostic_event"](
        store,
        {
            **base_event(),
            "type": "queue.lane.enqueue",
            "lane": "dreaming-narrative:session-main",
            "queueSize": 2,
        },
        TRUSTED,
    )

    rendered = test_api["render_prometheus_metrics"](store)

    assert 'openclaw_queue_lane_size{lane="dreaming-narrative"} 2' in rendered
    assert "session-main" not in rendered


def test_records_skill_usage_metrics_without_raw_paths_or_session_identifiers() -> None:
    store = test_api["create_prometheus_metric_store"]()

    test_api["record_diagnostic_event"](
        store,
        {
            **base_event(),
            "type": "skill.used",
            "agentId": "main",
            "runId": "run-should-not-export",
            "sessionKey": "session-should-not-export",
            "skillName": "tiny-llm-brainstorm",
            "skillSource": "workspace",
            "activation": "read",
            "toolName": "read",
        },
        TRUSTED,
    )

    rendered = test_api["render_prometheus_metrics"](store)

    assert "# TYPE openclaw_skill_used_total counter" in rendered
    assert (
        'openclaw_skill_used_total{activation="read",agent="main",skill="tiny-llm-brainstorm",source="workspace"} 1'
        in rendered
    )
    assert "run-should-not-export" not in rendered
    assert "session-should-not-export" not in rendered
    assert "SKILL.md" not in rendered


def test_bounds_messaging_labels_without_exporting_raw_chat_identifiers() -> None:
    store = test_api["create_prometheus_metric_store"]()

    test_api["record_diagnostic_event"](
        store,
        {
            **base_event(),
            "type": "message.delivery.started",
            "channel": "matrix",
            "deliveryKind": "text",
            "sessionKey": "session-should-not-export",
        },
        TRUSTED,
    )
    test_api["record_diagnostic_event"](
        store,
        {
            **base_event(),
            "type": "message.processed",
            "channel": "telegram/custom",
            "chatId": "chat-should-not-export",
            "messageId": "message-should-not-export",
            "outcome": "completed",
            "reason": "progress draft / message tool 123",
            "durationMs": 25,
        },
        TRUSTED,
    )
    test_api["record_diagnostic_event"](
        store,
        {
            **base_event(),
            "type": "message.delivery.error",
            "channel": "discord/custom",
            "deliveryKind": "progress draft",
            "durationMs": 50,
            "errorCategory": "TimeoutError",
        },
        TRUSTED,
    )

    rendered = test_api["render_prometheus_metrics"](store)

    assert (
        'openclaw_message_delivery_started_total{channel="matrix",delivery_kind="text"} 1'
        in rendered
    )
    assert (
        'openclaw_message_processed_total{channel="unknown",outcome="completed",reason="none"} 1'
        in rendered
    )
    assert (
        'openclaw_message_delivery_total{channel="unknown",delivery_kind="other",error_category="TimeoutError",outcome="error"} 1'
        in rendered
    )
    assert "chat-should-not-export" not in rendered
    assert "message-should-not-export" not in rendered
    assert "session-should-not-export" not in rendered
    assert "progress draft" not in rendered


def test_records_inbound_dispatch_and_session_turn_telemetry() -> None:
    store = test_api["create_prometheus_metric_store"]()

    test_api["record_diagnostic_event"](
        store,
        {
            **base_event(),
            "type": "message.received",
            "channel": "telegram",
            "source": "webhook",
        },
        TRUSTED,
    )
    test_api["record_diagnostic_event"](
        store,
        {
            **base_event(),
            "type": "message.dispatch.started",
            "channel": "telegram",
            "source": "webhook",
        },
        TRUSTED,
    )
    test_api["record_diagnostic_event"](
        store,
        {
            **base_event(),
            "type": "message.dispatch.completed",
            "channel": "telegram",
            "source": "webhook",
            "durationMs": 250,
            "outcome": "completed",
        },
        TRUSTED,
    )
    test_api["record_diagnostic_event"](
        store,
        {
            **base_event(),
            "type": "message.dispatch.completed",
            "channel": "telegram/custom",
            "source": "webhook with secret sk-test",
            "durationMs": 300,
            "outcome": "completed",
            "reason": "progress draft / message tool 123",
        },
        TRUSTED,
    )
    test_api["record_diagnostic_event"](
        store,
        {
            **base_event(),
            "type": "session.turn.created",
            "runId": "run-should-not-export",
            "agentId": "agent.default",
            "channel": "telegram",
            "trigger": "user",
        },
        TRUSTED,
    )

    rendered = test_api["render_prometheus_metrics"](store)

    assert 'openclaw_message_received_total{channel="telegram",source="webhook"} 1' in rendered
    assert (
        'openclaw_message_dispatch_started_total{channel="telegram",source="webhook"} 1' in rendered
    )
    assert (
        'openclaw_message_dispatch_completed_total{channel="telegram",outcome="completed",reason="none",source="webhook"} 1'
        in rendered
    )
    assert (
        'openclaw_message_dispatch_duration_seconds_sum{channel="telegram",outcome="completed",reason="none",source="webhook"} 0.25'
        in rendered
    )
    assert (
        'openclaw_message_dispatch_completed_total{channel="unknown",outcome="completed",reason="none",source="unknown"} 1'
        in rendered
    )
    assert (
        'openclaw_message_dispatch_duration_seconds_sum{channel="unknown",outcome="completed",reason="none",source="unknown"} 0.3'
        in rendered
    )
    assert (
        'openclaw_session_turn_created_total{agent="agent.default",channel="telegram",trigger="user"} 1'
        in rendered
    )
    assert "run-should-not-export" not in rendered


def test_records_session_recovery_and_talk_metrics_without_exporting_raw_ids_or_content() -> None:
    store = test_api["create_prometheus_metric_store"]()

    test_api["record_diagnostic_event"](
        store,
        {
            **base_event(),
            "type": "session.recovery.completed",
            "sessionId": "session-should-not-export",
            "sessionKey": "key-should-not-export",
            "state": "processing",
            "stateGeneration": 2,
            "ageMs": 12_000,
            "queueDepth": 1,
            "reason": "startup-sweep",
            "activeWorkKind": "tool_call",
            "allowActiveAbort": True,
            "status": "released",
            "action": "abort-active-run",
        },
        TRUSTED,
    )
    test_api["record_diagnostic_event"](
        store,
        {
            **base_event(),
            "type": "talk.event",
            "sessionId": "talk-session-should-not-export",
            "turnId": "turn-should-not-export",
            "talkEventType": "input.audio.delta",
            "mode": "realtime",
            "transport": "gateway-relay",
            "brain": "agent-consult",
            "provider": "openai",
            "byteLength": 320,
        },
        TRUSTED,
    )

    rendered = test_api["render_prometheus_metrics"](store)

    assert (
        'openclaw_session_recovery_total{action="abort-active-run",active_work_kind="tool_call",state="processing",status="released"} 1'
        in rendered
    )
    assert (
        'openclaw_session_recovery_age_seconds_sum{action="abort-active-run",active_work_kind="tool_call",state="processing",status="released"} 12'
        in rendered
    )
    assert (
        'openclaw_talk_event_total{brain="agent-consult",event_type="input.audio.delta",mode="realtime",provider="openai",transport="gateway-relay"} 1'
        in rendered
    )
    assert (
        'openclaw_talk_audio_bytes_sum{brain="agent-consult",event_type="input.audio.delta",mode="realtime",provider="openai",transport="gateway-relay"} 320'
        in rendered
    )
    assert "session-should-not-export" not in rendered
    assert "key-should-not-export" not in rendered
    assert "talk-session-should-not-export" not in rendered
    assert "turn-should-not-export" not in rendered


def test_caps_metric_series_growth_and_reports_dropped_series() -> None:
    store = test_api["create_prometheus_metric_store"]()

    for model_index in range(2100):
        test_api["record_diagnostic_event"](
            store,
            {
                **base_event(),
                "type": "model.call.completed",
                "runId": f"run-{model_index}",
                "callId": f"call-{model_index}",
                "provider": "openai",
                "model": f"model.{model_index}",
                "durationMs": 10,
            },
            TRUSTED,
        )

    rendered = test_api["render_prometheus_metrics"](store)

    assert "# TYPE openclaw_prometheus_series_dropped_total counter" in rendered
    assert "openclaw_prometheus_series_dropped_total " in rendered


def test_subscribes_to_internal_diagnostics_and_renders_scrape_text() -> None:
    listeners: list[Any] = []
    emitted: list[Any] = []
    exporter = create_diagnostics_prometheus_exporter()
    unsubscribe = MagicMock()

    class FakeInternalDiagnostics:
        def emit(self, event: dict[str, Any]) -> None:
            emitted.append(event)

        def on_event(self, listener: Any) -> Any:
            listeners.append(listener)
            return unsubscribe

    exporter["service"].start(
        type(
            "Ctx",
            (),
            {
                "config": {},
                "state_dir": "/tmp/openclaw-prometheus-test",
                "logger": type(
                    "Logger",
                    (),
                    {
                        "info": lambda *_args, **_kwargs: None,
                        "warn": lambda *_args, **_kwargs: None,
                        "error": lambda *_args, **_kwargs: None,
                        "debug": lambda *_args, **_kwargs: None,
                    },
                )(),
                "internal_diagnostics": FakeInternalDiagnostics(),
            },
        )()
    )

    assert len(listeners) == 1
    listeners[0](
        {
            **base_event(),
            "type": "model.usage",
            "provider": "openai",
            "model": "gpt-5.4",
            "usage": {"input": 12, "output": 3, "total": 15},
        },
        TRUSTED,
        {},
    )

    assert emitted == [
        {
            "type": "telemetry.exporter",
            "exporter": "diagnostics-prometheus",
            "signal": "metrics",
            "status": "started",
            "reason": "configured",
        }
    ]
    assert (
        'openclaw_model_tokens_total{agent="unknown",channel="unknown",model="gpt-5.4",provider="openai",token_type="input"} 12'
        in exporter["render"]()
    )

    exporter["service"].stop()

    unsubscribe.assert_called_once()
    assert exporter["render"]() == ""
