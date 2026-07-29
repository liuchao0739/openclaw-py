import os
import time
import uuid
from typing import Any, Optional

from .acp_runtime_backend import (
    register_acp_runtime_backend,
    unregister_acp_runtime_backend,
)
from .config import resolve_acpx_plugin_config, to_acp_mcp_servers
from .config_schema import DEFAULT_ACPX_TIMEOUT_SECONDS
from .state import (
    ACPX_GATEWAY_INSTANCE_KEY,
    ACPX_GATEWAY_INSTANCE_MAX_ENTRIES,
    ACPX_GATEWAY_INSTANCE_NAMESPACE,
    normalize_acpx_gateway_instance_record,
)

ENABLE_STARTUP_PROBE_ENV = "OPENCLAW_ACPX_RUNTIME_STARTUP_PROBE"
SKIP_RUNTIME_PROBE_ENV = "OPENCLAW_SKIP_ACPX_RUNTIME_PROBE"
ACPX_BACKEND_ID = "acpx"


def resolve_acpx_timer_timeout_ms(timeout_seconds: Optional[float]) -> Optional[int]:
    if timeout_seconds is None:
        return None
    if not isinstance(timeout_seconds, (int, float)) or isinstance(timeout_seconds, bool):
        return None
    if timeout_seconds != timeout_seconds:
        return None
    ms = int(timeout_seconds * 1000)
    return max(ms, 1)


def _normalize_probe_agent(value: Optional[str]) -> Optional[str]:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    return normalized or None


def _resolve_allowed_agents_probe_agent(ctx: Any) -> Optional[str]:
    config = getattr(ctx, "config", None) if not isinstance(ctx, dict) else ctx.get("config")
    if not isinstance(config, dict):
        return None
    acp_config = config.get("acp") or {}
    if not isinstance(acp_config, dict):
        return None
    allowed_agents = acp_config.get("allowedAgents") or []
    if not isinstance(allowed_agents, list):
        return None
    for agent in allowed_agents:
        normalized = _normalize_probe_agent(agent if isinstance(agent, str) else None)
        if normalized:
            return normalized
    return None


def _should_run_startup_probe(env: Optional[dict] = None) -> bool:
    env_map = env if isinstance(env, dict) else os.environ
    return env_map.get(ENABLE_STARTUP_PROBE_ENV) != "0"


def _should_probe_runtime_at_startup(env: Optional[dict] = None) -> bool:
    env_map = env if isinstance(env, dict) else os.environ
    return _should_run_startup_probe(env_map) and env_map.get(SKIP_RUNTIME_PROBE_ENV) != "1"


def _open_gateway_instance_state_store(open_keyed_store):
    return open_keyed_store(
        namespace=ACPX_GATEWAY_INSTANCE_NAMESPACE,
        maxEntries=ACPX_GATEWAY_INSTANCE_MAX_ENTRIES,
    )


async def _resolve_gateway_instance_id(open_keyed_store) -> str:
    store = _open_gateway_instance_state_store(open_keyed_store)
    lookup_fn = getattr(store, "lookup", None)
    if lookup_fn is None:
        lookup_fn = store.get("lookup") if isinstance(store, dict) else None
    existing_record = None
    if callable(lookup_fn):
        existing_record = await lookup_fn(ACPX_GATEWAY_INSTANCE_KEY)
    existing = normalize_acpx_gateway_instance_record(existing_record)
    if existing:
        return existing["instanceId"]
    next_id = str(uuid.uuid4())
    register_fn = getattr(store, "register", None)
    if register_fn is None:
        register_fn = store.get("register") if isinstance(store, dict) else None
    if callable(register_fn):
        await register_fn(ACPX_GATEWAY_INSTANCE_KEY, {
            "instanceId": next_id,
            "createdAt": int(time.time() * 1000),
        })
    return next_id


def _format_doctor_failure_message(report: dict) -> str:
    if not isinstance(report, dict):
        return "Deepgram realtime transcription error"
    message = report.get("message", "")
    details = report.get("details") or []
    detail_parts = []
    for detail in details:
        if isinstance(detail, str):
            text = detail.strip()
            if text:
                detail_parts.append(text)
        elif isinstance(detail, (int, float, bool)):
            detail_parts.append(str(detail))
        elif isinstance(detail, dict):
            try:
                import json
                detail_parts.append(json.dumps(detail))
            except Exception:
                detail_parts.append(str(detail))
    detail_text = "; ".join(detail_parts).strip()
    return f"{message} ({detail_text})" if detail_text else message


class AcpxRuntimeService:
    def __init__(self, params: Optional[dict] = None) -> None:
        self._params = params or {}
        self._runtime = None
        self._lifecycle_revision = 0

    @property
    def id(self) -> str:
        return "acpx-runtime"

    async def start(self, ctx: Any) -> None:
        env = os.environ
        if env.get("OPENCLAW_SKIP_ACPX_RUNTIME") == "1":
            _log_info(ctx, "skipping embedded acpx runtime backend (OPENCLAW_SKIP_ACPX_RUNTIME=1)")
            return

        open_keyed_store = self._params.get("openKeyedStore")
        if not callable(open_keyed_store):
            raise RuntimeError("ACPX runtime service requires plugin keyed state")

        raw_config = self._params.get("pluginConfig")
        workspace_dir = _get_ctx_attr(ctx, "workspaceDir")
        base_plugin_config = resolve_acpx_plugin_config({
            "rawConfig": raw_config,
            "workspaceDir": workspace_dir,
        })
        probe_agent = base_plugin_config.get("probeAgent") or _resolve_allowed_agents_probe_agent(ctx)
        plugin_config = dict(base_plugin_config)
        plugin_config["probeAgent"] = probe_agent

        state_dir = plugin_config.get("stateDir", "")
        wrapper_root = os.path.join(_get_ctx_attr(ctx, "stateDir") or state_dir, "acpx")
        _ensure_dir(state_dir)
        _ensure_dir(wrapper_root)

        gateway_instance_id = await _resolve_gateway_instance_id(open_keyed_store)

        runtime_factory = self._params.get("runtimeFactory")
        if callable(runtime_factory):
            started_runtime = await _maybe_await(runtime_factory({
                "pluginConfig": plugin_config,
                "gatewayInstanceId": gateway_instance_id,
                "wrapperRoot": wrapper_root,
                "logger": _get_ctx_attr(ctx, "logger"),
            }))
        else:
            started_runtime = await _create_lazy_default_runtime({
                "pluginConfig": plugin_config,
                "gatewayInstanceId": gateway_instance_id,
                "wrapperRoot": wrapper_root,
                "logger": _get_ctx_attr(ctx, "logger"),
            })
        self._runtime = started_runtime

        should_probe = _should_probe_runtime_at_startup(env)
        register_acp_runtime_backend({
            "id": ACPX_BACKEND_ID,
            "runtime": started_runtime,
            **({"healthy": lambda: _runtime_is_healthy(self._runtime)} if should_probe else {}),
        })
        _log_info(ctx, f"embedded acpx runtime backend registered (cwd: {plugin_config.get('cwd')})")

        if not should_probe:
            return

        self._lifecycle_revision += 1
        current_revision = self._lifecycle_revision
        try:
            probe_fn = getattr(started_runtime, "probeAvailability", None)
            if callable(probe_fn):
                await probe_fn()
            if current_revision != self._lifecycle_revision:
                return
            if _runtime_is_healthy(started_runtime):
                _log_info(ctx, "embedded acpx runtime backend ready")
                return
            doctor_fn = getattr(started_runtime, "doctor", None)
            if callable(doctor_fn):
                doctor_report = await doctor_fn()
                if current_revision != self._lifecycle_revision:
                    return
                _log_warn(ctx, f"embedded acpx runtime backend probe failed: {_format_doctor_failure_message(doctor_report) if doctor_report else 'backend remained unhealthy after probe'}")
            else:
                _log_warn(ctx, "embedded acpx runtime backend probe failed: backend remained unhealthy after probe")
        except Exception as err:
            if current_revision != self._lifecycle_revision:
                return
            _log_warn(ctx, f"embedded acpx runtime setup failed: {err}")

    async def stop(self, ctx: Any = None) -> None:
        self._lifecycle_revision += 1
        unregister_acp_runtime_backend(ACPX_BACKEND_ID)
        self._runtime = None


def _get_ctx_attr(ctx: Any, name: str, default: Any = None) -> Any:
    if isinstance(ctx, dict):
        return ctx.get(name, default)
    return getattr(ctx, name, default)


def _ensure_dir(path: str) -> None:
    if path:
        os.makedirs(path, exist_ok=True)


def _runtime_is_healthy(runtime: Any) -> bool:
    if runtime is None:
        return False
    is_healthy_fn = getattr(runtime, "isHealthy", None)
    if callable(is_healthy_fn):
        try:
            return bool(is_healthy_fn())
        except Exception:
            return False
    return False


def _log_info(ctx: Any, message: str) -> None:
    logger = _get_ctx_attr(ctx, "logger")
    if logger is None:
        return
    info_fn = getattr(logger, "info", None) if not isinstance(logger, dict) else logger.get("info")
    if callable(info_fn):
        info_fn(message)


def _log_warn(ctx: Any, message: str) -> None:
    logger = _get_ctx_attr(ctx, "logger")
    if logger is None:
        return
    warn_fn = getattr(logger, "warn", None) if not isinstance(logger, dict) else logger.get("warn")
    if callable(warn_fn):
        warn_fn(message)


async def _maybe_await(value: Any) -> Any:
    if hasattr(value, "__await__"):
        return await value
    return value


async def _create_lazy_default_runtime(params: dict) -> Any:
    class _LazyRuntime:
        async def probe_availability(self) -> None:
            pass

        def is_healthy(self) -> bool:
            return False

        async def doctor(self) -> dict:
            return {"ok": False, "message": "acpx runtime not available"}

    return _LazyRuntime()


def create_acpx_runtime_service(params: Optional[dict] = None) -> AcpxRuntimeService:
    return AcpxRuntimeService(params)
