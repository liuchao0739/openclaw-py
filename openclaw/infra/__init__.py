from __future__ import annotations

from openclaw.infra.backoff import compute_backoff, sleep_with_abort
from openclaw.infra.errors import format_error_message, detect_error_kind
from openclaw.infra.home_dir import (
    resolve_effective_home_dir,
    resolve_home_relative_path,
)
from openclaw.infra.dotenv import load_dotenv
from openclaw.infra.file_lock import with_file_lock
from openclaw.infra.replace_file import replace_file_atomic
from openclaw.infra.abort_signal import (
    AbortSignal,
    AbortController,
    compute_backoff as compute_abort_backoff,
)
from openclaw.infra.file_lock_manager import (
    FileLock,
    FileLockManager,
    acquire_file_lock,
    release_file_lock,
)
from openclaw.infra.json_file import (
    JsonFile,
    read_json_file,
    write_json_file,
    read_json_file_if_exists,
)
from openclaw.infra.fs_safe import (
    FsSafeRoot,
    create_fs_root,
)
from openclaw.infra.path_utils import (
    resolve_path_env,
    resolve_path_guards,
    resolve_path_prepend,
    resolve_path_safety,
    is_path_inside,
    normalize_paths_in_config,
)
from openclaw.infra.plain_object import (
    is_plain_object,
    is_record,
    get_prototype_keys,
    deep_merge,
    pick_properties,
    omit_properties,
    parse_json_with_json5_fallback,
)
from openclaw.infra.ports import (
    is_port_available,
    find_available_port,
    get_process_using_port,
    format_port_listening_info,
)
from openclaw.infra.fetch import (
    fetch,
    HttpResponse,
    FetchError,
    AbortError,
)
from openclaw.infra.http_body import (
    HttpBody,
    HttpErrorBody,
)
from openclaw.infra.keyed_async_queue import (
    KeyedAsyncQueue,
    AsyncJsonlQueue,
)
from openclaw.infra.diagnostic_events import (
    diagnostic_event,
    format_diagnostic_event,
    detect_error_kind as detect_diagnostic_error_kind,
)
from openclaw.infra.diagnostic_trace_context import (
    DiagnosticTraceContext,
    DiagnosticSpan,
)
from openclaw.infra.tls.fingerprint import (
    compute_file_sha256,
    compute_string_sha256,
    compute_bytes_sha256,
    fingerprint_cert,
)
from openclaw.infra.format_time.format_duration import (
    format_duration,
    format_datetime,
    format_relative,
)
from openclaw.infra.net.hostname import (
    hostname_from_url,
    is_local_hostname,
)

__all__ = [
    "compute_backoff",
    "sleep_with_abort",
    "format_error_message",
    "detect_error_kind",
    "resolve_effective_home_dir",
    "resolve_home_relative_path",
    "load_dotenv",
    "with_file_lock",
    "replace_file_atomic",
    "AbortSignal",
    "AbortController",
    "compute_abort_backoff",
    "FileLock",
    "FileLockManager",
    "acquire_file_lock",
    "release_file_lock",
    "JsonFile",
    "read_json_file",
    "write_json_file",
    "read_json_file_if_exists",
    "FsSafeRoot",
    "create_fs_root",
    "resolve_path_env",
    "resolve_path_guards",
    "resolve_path_prepend",
    "resolve_path_safety",
    "is_path_inside",
    "normalize_paths_in_config",
    "is_plain_object",
    "is_record",
    "get_prototype_keys",
    "deep_merge",
    "pick_properties",
    "omit_properties",
    "parse_json_with_json5_fallback",
    "is_port_available",
    "find_available_port",
    "get_process_using_port",
    "format_port_listening_info",
    "fetch",
    "HttpResponse",
    "FetchError",
    "AbortError",
    "HttpBody",
    "HttpErrorBody",
    "KeyedAsyncQueue",
    "AsyncJsonlQueue",
    "diagnostic_event",
    "format_diagnostic_event",
    "detect_diagnostic_error_kind",
    "DiagnosticTraceContext",
    "DiagnosticSpan",
    "compute_file_sha256",
    "compute_string_sha256",
    "compute_bytes_sha256",
    "fingerprint_cert",
    "format_duration",
    "format_datetime",
    "format_relative",
    "hostname_from_url",
    "is_local_hostname",
]
