"""Logging package — types, state, redaction, diagnostics."""

from .types import ConsoleStyle, LoggerSettings
from .state import logging_state
from .redact_identifier import sha256_hex_prefix, redact_identifier
from .diagnostic_session_state import (
    diagnostic_session_states,
    get_diagnostic_session_state,
    peek_diagnostic_session_state,
    prune_diagnostic_session_states,
    is_diagnostic_session_state_current,
)
from .diagnostic_session_recovery import (
    resolve_stuck_session_recovery_ref,
    recovery_outcome_mutates_session_state,
    recovery_outcome_clears_queued_session_state,
    format_recovery_outcome,
)
from .diagnostic_session_recovery_coordinator import (
    request_stuck_session_recovery,
    request_stuck_session_recovery_outcome,
)
from .diagnostic_stability import (
    get_diagnostic_stability_snapshot,
    start_diagnostic_stability_recorder,
    stop_diagnostic_stability_recorder,
)
from .diagnostic_stability_bundle import (
    write_diagnostic_stability_bundle_sync,
    write_diagnostic_memory_pressure_bundle_sync,
)
from .diagnostic_support_bundle import (
    json_support_bundle_file,
    jsonl_support_bundle_file,
    text_support_bundle_file,
    write_support_bundle_zip,
)
from .diagnostic_support_redaction import (
    redact_path_for_support,
    redact_text_for_support,
    redact_support_string,
    sanitize_support_snapshot_value,
    sanitize_support_config_value,
)
from .diagnostic import (
    diagnostic_logger,
    log_webhook_received,
    log_webhook_processed,
    log_webhook_error,
    log_message_queued,
    log_message_received,
    log_message_dispatch_started,
    log_message_dispatch_completed,
    log_message_processed,
    log_session_turn_created,
    log_session_state_change,
    mark_diagnostic_session_progress,
    log_session_attention,
    log_run_attempt,
    log_tool_loop_action,
    log_active_runs,
    start_diagnostic_heartbeat,
    stop_diagnostic_heartbeat,
    resolve_stuck_session_warn_ms,
    resolve_stuck_session_abort_ms,
    is_stuck_session_recovery_enabled,
)

__all__ = [
    "ConsoleStyle",
    "LoggerSettings",
    "logging_state",
    "sha256_hex_prefix",
    "redact_identifier",
    "diagnostic_session_states",
    "get_diagnostic_session_state",
    "peek_diagnostic_session_state",
    "prune_diagnostic_session_states",
    "is_diagnostic_session_state_current",
    "resolve_stuck_session_recovery_ref",
    "recovery_outcome_mutates_session_state",
    "recovery_outcome_clears_queued_session_state",
    "format_recovery_outcome",
    "request_stuck_session_recovery",
    "request_stuck_session_recovery_outcome",
    "get_diagnostic_stability_snapshot",
    "start_diagnostic_stability_recorder",
    "stop_diagnostic_stability_recorder",
    "write_diagnostic_stability_bundle_sync",
    "write_diagnostic_memory_pressure_bundle_sync",
    "json_support_bundle_file",
    "jsonl_support_bundle_file",
    "text_support_bundle_file",
    "write_support_bundle_zip",
    "redact_path_for_support",
    "redact_text_for_support",
    "redact_support_string",
    "sanitize_support_snapshot_value",
    "sanitize_support_config_value",
    "diagnostic_logger",
    "log_webhook_received",
    "log_webhook_processed",
    "log_webhook_error",
    "log_message_queued",
    "log_message_received",
    "log_message_dispatch_started",
    "log_message_dispatch_completed",
    "log_message_processed",
    "log_session_turn_created",
    "log_session_state_change",
    "mark_diagnostic_session_progress",
    "log_session_attention",
    "log_run_attempt",
    "log_tool_loop_action",
    "log_active_runs",
    "start_diagnostic_heartbeat",
    "stop_diagnostic_heartbeat",
    "resolve_stuck_session_warn_ms",
    "resolve_stuck_session_abort_ms",
    "is_stuck_session_recovery_enabled",
]
