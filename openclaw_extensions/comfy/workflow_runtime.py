"""Comfy workflow runtime for local and cloud ComfyUI media generation."""

from __future__ import annotations

import asyncio
import copy
import ipaddress
import json
import mimetypes
import os
import socket
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlencode, urlparse

from openclaw.config.secrets import coerce_secret_ref, normalize_secret_input_string
from openclaw.infra.paths import resolve_user_path
from openclaw.packages.normalization_core import (
    is_record,
    normalize_optional_lowercase_string,
    normalize_optional_string,
    resolve_positive_timer_timeout_ms,
    unique_strings,
)
from openclaw.plugin_sdk.provider_auth import is_provider_api_key_configured
from openclaw.plugin_sdk.provider_auth_runtime import resolve_api_key_for_provider
from openclaw.plugin_sdk.provider_http import (
    assert_ok_or_throw_http_error,
    read_response_with_limit,
    resolve_provider_http_request_config,
)

DEFAULT_COMFY_LOCAL_BASE_URL = "http://127.0.0.1:8188"
DEFAULT_COMFY_CLOUD_BASE_URL = "https://cloud.comfy.org"
DEFAULT_PROMPT_INPUT_NAME = "text"
DEFAULT_INPUT_IMAGE_INPUT_NAME = "image"
DEFAULT_POLL_INTERVAL_MS = 1_500
DEFAULT_TIMEOUT_MS = 5 * 60_000
DEFAULT_GENERATED_IMAGE_MAX_BYTES = 6 * 1024 * 1024
DEFAULT_GENERATED_MEDIA_MAX_BYTES = 16 * 1024 * 1024

DEFAULT_COMFY_MODEL = "workflow"

ComfyMode = Literal["local", "cloud"]
ComfyCapability = Literal["image", "music", "video"]
ComfyOutputKind = Literal["audio", "gifs", "images", "videos"]

ComfyFetchGuard = Callable[..., Awaitable[dict[str, Any]]]

_comfy_fetch_guard_override: ComfyFetchGuard | None = None


class ComfyMultipartForm:
    """Multipart upload body used for Comfy image uploads."""

    def __init__(
        self,
        *,
        fields: dict[str, str],
        files: dict[str, tuple[str, bytes, str]],
    ) -> None:
        self._fields = fields
        self._files = files

    def get(self, key: str) -> str | None:
        return self._fields.get(key)


def set_comfy_fetch_guard_for_testing(impl: ComfyFetchGuard | None) -> None:
    """Override the SSRF-guarded fetch implementation for tests."""
    global _comfy_fetch_guard_override
    _comfy_fetch_guard_override = impl


def _default_fetch_fn(url: str, init: dict[str, Any], *, timeout_ms: int) -> Any:
    import httpx

    timeout_seconds = max(1, timeout_ms) / 1000
    with httpx.Client(timeout=timeout_seconds) as client:
        return client.request(
            init.get("method", "GET"),
            url,
            headers=init.get("headers"),
            content=init.get("body"),
        )


async def _fetch_with_ssrf_guard(
    *,
    url: str,
    init: dict[str, Any] | None = None,
    timeout_ms: int | None = None,
    policy: dict[str, Any] | None = None,
    dispatcher_policy: Any = None,
    audit_context: str | None = None,
    fetch_fn: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    del dispatcher_policy, audit_context
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    allowlist = (policy or {}).get("hostnameAllowlist") or []
    if allowlist and hostname not in allowlist:
        msg = f"Blocked hostname in guarded fetch: {hostname}"
        raise RuntimeError(msg)

    resolved_timeout = resolve_positive_timer_timeout_ms(timeout_ms, DEFAULT_TIMEOUT_MS)
    resolved_fetch = fetch_fn or _default_fetch_fn

    class _GuardResponse:
        def __init__(self, response: Any) -> None:
            self.ok = bool(getattr(response, "is_success", getattr(response, "ok", False)))
            self.status = getattr(response, "status_code", getattr(response, "status", 0))
            self.headers = getattr(response, "headers", {})
            self._response = response

        async def json(self) -> Any:
            if hasattr(self._response, "json"):
                result = self._response.json()
                if asyncio.iscoroutine(result):
                    return await result
                return result
            raise AttributeError("response has no json()")

        async def aread(self) -> bytes:
            if hasattr(self._response, "aread"):
                return await self._response.aread()
            if hasattr(self._response, "content"):
                content = self._response.content
                if asyncio.iscoroutine(content):
                    return await content
                return content
            return self._response.read()

    response = await asyncio.to_thread(
        resolved_fetch,
        url,
        init or {},
        timeout_ms=resolved_timeout,
    )
    wrapped = _GuardResponse(response)

    async def release() -> None:
        return None

    return {"response": wrapped, "release": release}


async def _invoke_comfy_fetch_guard(params: dict[str, Any]) -> dict[str, Any]:
    if _comfy_fetch_guard_override is not None:
        result = _comfy_fetch_guard_override(params)
        if asyncio.iscoroutine(result):
            return await result
        return result
    return await _fetch_with_ssrf_guard(
        url=params["url"],
        init=params.get("init"),
        timeout_ms=params.get("timeoutMs"),
        policy=params.get("policy"),
        dispatcher_policy=params.get("dispatcherPolicy"),
        audit_context=params.get("auditContext"),
    )


def _normalize_base_url(base_url: str | None) -> str | None:
    raw = normalize_optional_string(base_url)
    if not raw:
        return None
    return raw.rstrip("/")


def _as_boolean(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _read_config_boolean(config: dict[str, Any], key: str) -> bool | None:
    return _as_boolean(config.get(key))


def _read_config_integer(config: dict[str, Any], key: str) -> int | None:
    value = config.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def get_comfy_config(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    plugins = cfg.get("plugins") if is_record(cfg) else None
    entries = plugins.get("entries") if is_record(plugins) else None
    comfy_entry = entries.get("comfy") if is_record(entries) else None
    plugin_config = comfy_entry.get("config") if is_record(comfy_entry) else None
    if is_record(plugin_config):
        return plugin_config
    models = cfg.get("models") if is_record(cfg) else None
    providers = models.get("providers") if is_record(models) else None
    legacy_config = providers.get("comfy") if is_record(providers) else None
    return legacy_config if is_record(legacy_config) else {}


def _strip_nested_capability_config(config: dict[str, Any]) -> dict[str, Any]:
    next_config = dict(config)
    next_config.pop("image", None)
    next_config.pop("video", None)
    next_config.pop("music", None)
    return next_config


def _get_comfy_capability_config(
    config: dict[str, Any],
    capability: ComfyCapability,
) -> dict[str, Any]:
    shared = _strip_nested_capability_config(config)
    nested = config.get(capability)
    if not is_record(nested):
        return shared
    return {**shared, **nested}


def _resolve_comfy_mode(config: dict[str, Any]) -> ComfyMode:
    return "cloud" if normalize_optional_string(config.get("mode")) == "cloud" else "local"


def _resolve_default_secret_provider_alias(cfg: dict[str, Any], source: str = "env") -> str:
    secrets = cfg.get("secrets")
    if is_record(secrets):
        defaults = secrets.get("defaults")
        if is_record(defaults):
            configured = defaults.get(source)
            if isinstance(configured, str) and configured.strip():
                return configured.strip()
    return "default"


def _can_resolve_env_secret_ref_in_read_only_path(
    *,
    cfg: dict[str, Any] | None,
    provider: str,
    ref_id: str,
) -> bool:
    provider_config = None
    if cfg and is_record(cfg.get("secrets")):
        providers = cfg["secrets"].get("providers")
        if is_record(providers):
            provider_config = providers.get(provider)
    if not provider_config:
        return provider == _resolve_default_secret_provider_alias(cfg or {}, "env")
    if provider_config.get("source") != "env":
        return False
    allowlist = provider_config.get("allowlist")
    return not isinstance(allowlist, list) or ref_id in allowlist


def _resolve_secret_input_string(
    *,
    value: Any,
    path: str,
    defaults: Any = None,
) -> dict[str, Any]:
    del path, defaults
    normalized = normalize_secret_input_string(value)
    if normalized:
        return {"status": "available", "value": normalized, "ref": None}
    ref = coerce_secret_ref(value)
    if not ref:
        return {"status": "missing", "value": None, "ref": None}
    return {
        "status": "configured_unavailable",
        "value": None,
        "ref": {
            "source": ref["source"],
            "provider": ref["provider"],
            "id": ref["id"],
        },
    }


def _resolve_comfy_api_key(
    config: dict[str, Any],
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    defaults = None
    if cfg and is_record(cfg.get("secrets")):
        defaults = cfg["secrets"].get("defaults")
    resolved = _resolve_secret_input_string(
        value=config.get("apiKey"),
        path="plugins.entries.comfy.config.apiKey",
        defaults=defaults,
    )
    if resolved["status"] == "available":
        api_key = normalize_secret_input_string(resolved["value"])
        if api_key:
            return {
                "status": "available",
                "apiKey": api_key,
                "source": "plugins.entries.comfy.config.apiKey",
            }
        return {"status": "missing"}
    if resolved["status"] == "configured_unavailable":
        ref = resolved["ref"]
        if not is_record(ref) or ref.get("source") != "env":
            return {"status": "configured_unavailable"}
        env_var_name = str(ref.get("id") or "").strip()
        if not _can_resolve_env_secret_ref_in_read_only_path(
            cfg=cfg,
            provider=str(ref.get("provider") or ""),
            ref_id=env_var_name,
        ):
            return {"status": "configured_unavailable"}
        api_key = normalize_secret_input_string(os.environ.get(env_var_name))
        if api_key:
            return {
                "status": "available",
                "apiKey": api_key,
                "source": f"plugins.entries.comfy.config.apiKey ({env_var_name})",
            }
        return {"status": "configured_unavailable"}
    return {"status": "missing"}


def _get_required_config_string(config: dict[str, Any], key: str) -> str:
    value = normalize_optional_string(config.get(key))
    if not value:
        raise ValueError(f"plugins.entries.comfy.config.{key} is required")
    return value


def _resolve_comfy_workflow_source(
    config: dict[str, Any],
) -> dict[str, Any]:
    workflow = config.get("workflow")
    if is_record(workflow):
        return {"workflow": copy.deepcopy(workflow)}
    workflow_path = normalize_optional_string(config.get("workflowPath"))
    return {"workflowPath": workflow_path}


async def _load_comfy_workflow(config: dict[str, Any]) -> dict[str, Any]:
    source = _resolve_comfy_workflow_source(config)
    workflow = source.get("workflow")
    if is_record(workflow):
        return workflow
    workflow_path = normalize_optional_string(source.get("workflowPath"))
    if not workflow_path:
        raise ValueError(
            "plugins.entries.comfy.config.<capability>.workflow or workflowPath is required",
        )
    resolved_path = resolve_user_path(workflow_path)
    raw = await asyncio.to_thread(Path(resolved_path).read_text, encoding="utf-8")
    parsed = json.loads(raw)
    if not is_record(parsed):
        raise ValueError(f"Comfy workflow at {resolved_path} must be a JSON object")
    return parsed


def _set_workflow_input(
    *,
    workflow: dict[str, Any],
    node_id: str,
    input_name: str,
    value: Any,
) -> None:
    node = workflow.get(node_id)
    if not is_record(node):
        raise ValueError(f'Comfy workflow missing node "{node_id}"')
    inputs = node.get("inputs")
    if not is_record(inputs):
        raise ValueError(f'Comfy workflow node "{node_id}" is missing an inputs object')
    inputs[input_name] = value


def _is_private_or_loopback_host(hostname: str) -> bool:
    lowered = hostname.lower()
    if lowered in {"localhost", "127.0.0.1", "::1"} or lowered.endswith(".local"):
        return True
    try:
        address = ipaddress.ip_address(lowered)
        return address.is_private or address.is_loopback
    except ValueError:
        try:
            infos = socket.getaddrinfo(hostname, None)
        except OSError:
            return False
        if not infos:
            return False
        return all(
            ipaddress.ip_address(info[4][0]).is_private or ipaddress.ip_address(info[4][0]).is_loopback
            for info in infos
            if info[4]
        )


def _resolve_comfy_network_policy(
    *,
    base_url: str,
    allow_private_network: bool,
) -> dict[str, Any]:
    try:
        parsed = urlparse(base_url)
    except ValueError:
        return {}
    hostname = normalize_optional_lowercase_string(parsed.hostname) or ""
    if not hostname or not allow_private_network or not _is_private_or_loopback_host(hostname):
        return {}
    return {"apiPolicy": {"hostnameAllowlist": [hostname]}}


async def _read_json_response(params: dict[str, Any]) -> Any:
    guarded = await _invoke_comfy_fetch_guard(params)
    response = guarded["response"]
    release: Callable[[], Awaitable[None]] = guarded["release"]
    try:
        await assert_ok_or_throw_http_error(response, params["errorPrefix"])
        try:
            if hasattr(response, "json"):
                return await response.json()
            raw = await response.aread()
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, TypeError, ValueError) as cause:
            raise RuntimeError(
                f"{params['errorPrefix']}: malformed JSON response",
            ) from cause
    finally:
        await release()


def _extension_for_mime(mime_type: str | None) -> str | None:
    normalized = normalize_optional_string(mime_type)
    if not normalized:
        return None
    extension = mimetypes.guess_extension(normalized.split(";", 1)[0].strip())
    return extension


def _resolve_file_extension(*, file_name: str | None = None, mime_type: str | None = None) -> str:
    extension = _extension_for_mime(mime_type)
    if extension:
        return extension.removeprefix(".")
    normalized_name = normalize_optional_string(file_name)
    if not normalized_name:
        return "bin"
    dot_index = normalized_name.rfind(".")
    if dot_index < 0 or dot_index == len(normalized_name) - 1:
        return "bin"
    return normalized_name[dot_index + 1 :]


async def _upload_input_image(params: dict[str, Any]) -> str:
    image = params["image"]
    file_name = (
        normalize_optional_string(image.get("fileName"))
        or f"input.{_resolve_file_extension(mime_type=image.get('mimeType'))}"
    )
    form = ComfyMultipartForm(
        fields={"type": "input", "overwrite": "true"},
        files={
            "image": (
                file_name,
                bytes(image["buffer"]),
                str(image.get("mimeType") or "application/octet-stream"),
            ),
        },
    )
    headers = dict(params["headers"])
    headers.pop("Content-Type", None)
    headers.pop("content-type", None)
    payload = await _read_json_response(
        {
            "url": (
                f"{params['baseUrl']}"
                f"{ '/api/upload/image' if params['mode'] == 'cloud' else '/upload/image'}"
            ),
            "init": {
                "method": "POST",
                "headers": headers,
                "body": form,
            },
            "timeoutMs": params["timeoutMs"],
            "policy": params.get("policy"),
            "dispatcherPolicy": params.get("dispatcherPolicy"),
            "auditContext": f"comfy-{params['capability']}-upload",
            "errorPrefix": "Comfy image upload failed",
        }
    )
    if not is_record(payload):
        raise RuntimeError("Comfy image upload failed: malformed JSON response")
    uploaded_name = normalize_optional_string(payload.get("filename")) or normalize_optional_string(
        payload.get("name")
    )
    if not uploaded_name:
        raise RuntimeError("Comfy image upload response missing filename")
    return uploaded_name


def _extract_history_entry(history: Any, prompt_id: str) -> dict[str, Any] | None:
    if not is_record(history):
        return None
    direct_outputs = history.get("outputs")
    if is_record(direct_outputs):
        return history
    nested = history.get(prompt_id)
    return nested if is_record(nested) else None


async def _wait_for_local_history(params: dict[str, Any]) -> dict[str, Any]:
    deadline = int(time.time() * 1000) + params["timeoutMs"]
    while True:
        request_timeout_ms = _resolve_comfy_remaining_ms(
            deadline,
            params["timeoutMs"],
        )
        history = await _read_json_response(
            {
                "url": f"{params['baseUrl']}/history/{params['promptId']}",
                "init": {
                    "method": "GET",
                    "headers": params["headers"],
                },
                "timeoutMs": request_timeout_ms,
                "policy": params.get("policy"),
                "dispatcherPolicy": params.get("dispatcherPolicy"),
                "auditContext": "comfy-history",
                "errorPrefix": "Comfy history lookup failed",
            }
        )
        entry = _extract_history_entry(history, params["promptId"])
        outputs = entry.get("outputs") if is_record(entry) else None
        if is_record(outputs) and outputs:
            return entry
        poll_delay_ms = _resolve_comfy_remaining_ms(
            deadline,
            params["timeoutMs"],
            params["pollIntervalMs"],
        )
        await asyncio.sleep(poll_delay_ms / 1000)


async def _wait_for_cloud_completion(params: dict[str, Any]) -> None:
    deadline = int(time.time() * 1000) + params["timeoutMs"]
    while True:
        request_timeout_ms = _resolve_comfy_remaining_ms(
            deadline,
            params["timeoutMs"],
        )
        status_payload = await _read_json_response(
            {
                "url": f"{params['baseUrl']}/api/job/{params['promptId']}/status",
                "init": {
                    "method": "GET",
                    "headers": params["headers"],
                },
                "timeoutMs": request_timeout_ms,
                "policy": params.get("policy"),
                "dispatcherPolicy": params.get("dispatcherPolicy"),
                "auditContext": "comfy-status",
                "errorPrefix": "Comfy status lookup failed",
            }
        )
        if not is_record(status_payload):
            raise RuntimeError("Comfy status lookup failed: malformed JSON response")
        status = status_payload.get("status")
        if status == "completed":
            return
        if status in {"failed", "cancelled"}:
            error = status_payload.get("error") or status_payload.get("message") or params["promptId"]
            raise RuntimeError(f"Comfy workflow {status}: {error}")
        poll_delay_ms = _resolve_comfy_remaining_ms(
            deadline,
            params["timeoutMs"],
            params["pollIntervalMs"],
        )
        await asyncio.sleep(poll_delay_ms / 1000)


def _resolve_comfy_remaining_ms(
    deadline: int,
    timeout_ms: int,
    default_timeout_ms: int | None = None,
) -> int:
    default_ms = resolve_positive_timer_timeout_ms(
        default_timeout_ms if default_timeout_ms is not None else timeout_ms,
        1,
    )
    remaining_ms = deadline - int(time.time() * 1000)
    if remaining_ms <= 0:
        raise RuntimeError(f"Comfy workflow did not finish within {((timeout_ms + 999) // 1000)}s")
    return max(1, min(default_ms, remaining_ms))


def _collect_output_files(
    *,
    history: dict[str, Any],
    output_node_id: str | None = None,
    output_kinds: list[ComfyOutputKind] | tuple[ComfyOutputKind, ...],
) -> list[dict[str, Any]]:
    outputs = history.get("outputs")
    if not is_record(outputs):
        return []
    node_ids = [output_node_id] if output_node_id else list(outputs.keys())
    files: list[dict[str, Any]] = []
    for node_id in node_ids:
        entry = outputs.get(node_id)
        if not is_record(entry):
            continue
        for kind in output_kinds:
            bucket = entry.get(kind)
            if not isinstance(bucket, list):
                continue
            for file in bucket:
                if is_record(file):
                    files.append({"nodeId": node_id, "file": file})
    return files


async def _download_output_file(params: dict[str, Any]) -> dict[str, Any]:
    file = params["file"]
    file_name = normalize_optional_string(file.get("filename")) or normalize_optional_string(
        file.get("name")
    )
    if not file_name:
        raise RuntimeError("Comfy output entry missing filename")
    query = urlencode(
        {
            "filename": file_name,
            "subfolder": normalize_optional_string(file.get("subfolder")) or "",
            "type": normalize_optional_string(file.get("type")) or "output",
        }
    )
    view_path = "/api/view" if params["mode"] == "cloud" else "/view"
    audit_context = f"comfy-{params['capability']}-download"
    first_response = await _invoke_comfy_fetch_guard(
        {
            "url": f"{params['baseUrl']}{view_path}?{query}",
            "init": {
                "method": "GET",
                "headers": params["headers"],
                **({"redirect": "manual"} if params["mode"] == "cloud" else {}),
            },
            "timeoutMs": params["timeoutMs"],
            "policy": params.get("policy"),
            "dispatcherPolicy": params.get("dispatcherPolicy"),
            "auditContext": audit_context,
        }
    )
    try:
        response = first_response["response"]
        if params["mode"] == "cloud" and response.status in {301, 302, 303, 307, 308}:
            headers = response.headers
            redirect_url = normalize_optional_string(
                headers.get("location") if hasattr(headers, "get") else headers.get("Location")
            )
            if not redirect_url:
                raise RuntimeError("Comfy cloud output redirect missing location header")
            redirected = await _invoke_comfy_fetch_guard(
                {
                    "url": redirect_url,
                    "init": {"method": "GET"},
                    "timeoutMs": params["timeoutMs"],
                    "dispatcherPolicy": params.get("dispatcherPolicy"),
                    "auditContext": audit_context,
                }
            )
            try:
                redirect_response = redirected["response"]
                await assert_ok_or_throw_http_error(redirect_response, "Comfy output download failed")
                redirect_headers = redirect_response.headers
                mime_type = (
                    normalize_optional_string(
                        redirect_headers.get("content-type")
                        if hasattr(redirect_headers, "get")
                        else None
                    )
                    or "application/octet-stream"
                )
                return {
                    "buffer": await read_response_with_limit(
                        redirect_response,
                        params["maxBytes"],
                        on_overflow=lambda overflow: RuntimeError(
                            f"Comfy {params['capability']} output download exceeds "
                            f"{overflow['maxBytes']} bytes"
                        ),
                    ),
                    "mimeType": mime_type,
                }
            finally:
                await redirected["release"]()
        await assert_ok_or_throw_http_error(response, "Comfy output download failed")
        response_headers = response.headers
        mime_type = (
            normalize_optional_string(
                response_headers.get("content-type") if hasattr(response_headers, "get") else None
            )
            or "application/octet-stream"
        )
        return {
            "buffer": await read_response_with_limit(
                response,
                params["maxBytes"],
                on_overflow=lambda overflow: RuntimeError(
                    f"Comfy {params['capability']} output download exceeds {overflow['maxBytes']} bytes"
                ),
            ),
            "mimeType": mime_type,
        }
    finally:
        await first_response["release"]()


def _resolve_comfy_generated_output_max_bytes(
    *,
    cfg: dict[str, Any],
    capability: ComfyCapability,
) -> int:
    agents = cfg.get("agents") if is_record(cfg) else None
    defaults = agents.get("defaults") if is_record(agents) else None
    configured = defaults.get("mediaMaxMb") if is_record(defaults) else None
    if isinstance(configured, (int, float)) and configured > 0:
        return int(configured * 1024 * 1024)
    return (
        DEFAULT_GENERATED_IMAGE_MAX_BYTES
        if capability == "image"
        else DEFAULT_GENERATED_MEDIA_MAX_BYTES
    )


def is_comfy_capability_configured(params: dict[str, Any]) -> bool:
    config = get_comfy_config(params.get("cfg"))
    capability_config = _get_comfy_capability_config(config, params["capability"])
    workflow_source = _resolve_comfy_workflow_source(capability_config)
    has_workflow = bool(
        workflow_source.get("workflow")
        or normalize_optional_string(workflow_source.get("workflowPath"))
    )
    has_prompt_node = bool(normalize_optional_string(capability_config.get("promptNodeId")))
    if not has_workflow or not has_prompt_node:
        return False
    if _resolve_comfy_mode(capability_config) == "local":
        return True
    configured_api_key = _resolve_comfy_api_key(capability_config, params.get("cfg"))
    if configured_api_key["status"] == "available":
        return True
    if configured_api_key["status"] == "configured_unavailable":
        return False
    return is_provider_api_key_configured(
        {
            "provider": "comfy",
            "agentDir": params.get("agentDir"),
        }
    )


async def run_comfy_workflow(params: dict[str, Any]) -> dict[str, Any]:
    cfg = params["cfg"]
    config = get_comfy_config(cfg)
    capability_config = _get_comfy_capability_config(config, params["capability"])
    mode = _resolve_comfy_mode(capability_config)
    workflow = await _load_comfy_workflow(capability_config)
    prompt_node_id = _get_required_config_string(capability_config, "promptNodeId")
    prompt_input_name = (
        normalize_optional_string(capability_config.get("promptInputName"))
        or DEFAULT_PROMPT_INPUT_NAME
    )
    input_image_node_id = normalize_optional_string(capability_config.get("inputImageNodeId"))
    input_image_input_name = (
        normalize_optional_string(capability_config.get("inputImageInputName"))
        or DEFAULT_INPUT_IMAGE_INPUT_NAME
    )
    output_node_id = normalize_optional_string(capability_config.get("outputNodeId"))
    poll_interval_ms = resolve_positive_timer_timeout_ms(
        _read_config_integer(capability_config, "pollIntervalMs"),
        DEFAULT_POLL_INTERVAL_MS,
    )
    timeout_ms = resolve_positive_timer_timeout_ms(
        _read_config_integer(capability_config, "timeoutMs") or params.get("timeoutMs"),
        DEFAULT_TIMEOUT_MS,
    )
    provider_model = normalize_optional_string(params.get("model")) or DEFAULT_COMFY_MODEL

    _set_workflow_input(
        workflow=workflow,
        node_id=prompt_node_id,
        input_name=prompt_input_name,
        value=params["prompt"],
    )

    plugin_api_key = _resolve_comfy_api_key(capability_config, cfg)
    resolved_auth = None
    if mode == "cloud":
        if plugin_api_key["status"] == "available":
            resolved_auth = {
                "apiKey": plugin_api_key["apiKey"],
                "source": plugin_api_key["source"],
                "mode": "api-key",
            }
        elif plugin_api_key["status"] != "configured_unavailable":
            resolved_auth = await resolve_api_key_for_provider(
                {
                    "provider": "comfy",
                    "cfg": cfg,
                    "agentDir": params.get("agentDir"),
                    "store": params.get("authStore"),
                }
            )
    if mode == "cloud" and not (resolved_auth or {}).get("apiKey"):
        raise RuntimeError("Comfy Cloud API key missing")

    request_config = resolve_provider_http_request_config(
        {
            "baseUrl": normalize_optional_string(capability_config.get("baseUrl")),
            "defaultBaseUrl": (
                DEFAULT_COMFY_CLOUD_BASE_URL if mode == "cloud" else DEFAULT_COMFY_LOCAL_BASE_URL
            ),
            "allowPrivateNetwork": mode == "local"
            or _read_config_boolean(capability_config, "allowPrivateNetwork") is True,
            "defaultHeaders": (
                {
                    "X-API-Key": (resolved_auth or {}).get("apiKey") or "",
                    "Content-Type": "application/json",
                }
                if mode == "cloud"
                else {"Content-Type": "application/json"}
            ),
            "provider": "comfy",
            "capability": "audio" if params["capability"] == "music" else params["capability"],
            "transport": "http",
        }
    )
    normalized_base_url = _normalize_base_url(request_config["baseUrl"]) or (
        DEFAULT_COMFY_CLOUD_BASE_URL if mode == "cloud" else DEFAULT_COMFY_LOCAL_BASE_URL
    )
    network_policy = _resolve_comfy_network_policy(
        base_url=normalized_base_url,
        allow_private_network=bool(request_config["allowPrivateNetwork"]),
    )
    headers = dict(request_config["headers"])
    dispatcher_policy = request_config.get("dispatcherPolicy")

    input_image = params.get("inputImage")
    if input_image:
        if not input_image_node_id:
            raise RuntimeError(
                "Comfy edit requests require "
                "plugins.entries.comfy.config.<capability>.inputImageNodeId to be configured",
            )
        uploaded_name = await _upload_input_image(
            {
                "baseUrl": normalized_base_url,
                "headers": headers,
                "timeoutMs": timeout_ms,
                "policy": network_policy.get("apiPolicy"),
                "dispatcherPolicy": dispatcher_policy,
                "image": input_image,
                "mode": mode,
                "capability": params["capability"],
            }
        )
        _set_workflow_input(
            workflow=workflow,
            node_id=input_image_node_id,
            input_name=input_image_input_name,
            value=uploaded_name,
        )

    submit_payload: dict[str, Any] = {"prompt": workflow}
    if mode == "cloud" and (resolved_auth or {}).get("apiKey"):
        submit_payload["extra_data"] = {"api_key_comfy_org": resolved_auth["apiKey"]}

    prompt_response = await _read_json_response(
        {
            "url": f"{normalized_base_url}{'/api/prompt' if mode == 'cloud' else '/prompt'}",
            "init": {
                "method": "POST",
                "headers": headers,
                "body": json.dumps(submit_payload),
            },
            "timeoutMs": timeout_ms,
            "policy": network_policy.get("apiPolicy"),
            "dispatcherPolicy": dispatcher_policy,
            "auditContext": f"comfy-{params['capability']}-generate",
            "errorPrefix": "Comfy workflow submit failed",
        }
    )
    if not is_record(prompt_response):
        raise RuntimeError("Comfy workflow submit failed: malformed JSON response")
    prompt_id = normalize_optional_string(prompt_response.get("prompt_id"))
    if not prompt_id:
        raise RuntimeError("Comfy workflow submit response missing prompt_id")

    if mode == "cloud":
        await _wait_for_cloud_completion(
            {
                "baseUrl": normalized_base_url,
                "promptId": prompt_id,
                "headers": dict(headers),
                "timeoutMs": timeout_ms,
                "pollIntervalMs": poll_interval_ms,
                "policy": network_policy.get("apiPolicy"),
                "dispatcherPolicy": dispatcher_policy,
            }
        )
        history = await _read_json_response(
            {
                "url": f"{normalized_base_url}/api/history_v2/{prompt_id}",
                "init": {
                    "method": "GET",
                    "headers": dict(headers),
                },
                "timeoutMs": timeout_ms,
                "policy": network_policy.get("apiPolicy"),
                "dispatcherPolicy": dispatcher_policy,
                "auditContext": "comfy-history",
                "errorPrefix": "Comfy history lookup failed",
            }
        )
    else:
        history = await _wait_for_local_history(
            {
                "baseUrl": normalized_base_url,
                "promptId": prompt_id,
                "headers": dict(headers),
                "timeoutMs": timeout_ms,
                "pollIntervalMs": poll_interval_ms,
                "policy": network_policy.get("apiPolicy"),
                "dispatcherPolicy": dispatcher_policy,
            }
        )

    history_entry = _extract_history_entry(history, prompt_id)
    if not history_entry:
        raise RuntimeError(f"Comfy history response missing outputs for prompt {prompt_id}")

    output_files = _collect_output_files(
        history=history_entry,
        output_node_id=output_node_id,
        output_kinds=params["outputKinds"],
    )
    if not output_files:
        raise RuntimeError(
            f"Comfy workflow {prompt_id} completed without {params['capability']} outputs",
        )

    assets: list[dict[str, Any]] = []
    max_output_bytes = _resolve_comfy_generated_output_max_bytes(
        cfg=cfg,
        capability=params["capability"],
    )
    for asset_index, output in enumerate(output_files, start=1):
        downloaded = await _download_output_file(
            {
                "baseUrl": normalized_base_url,
                "headers": dict(headers),
                "timeoutMs": timeout_ms,
                "policy": network_policy.get("apiPolicy"),
                "dispatcherPolicy": dispatcher_policy,
                "file": output["file"],
                "mode": mode,
                "capability": params["capability"],
                "maxBytes": max_output_bytes,
            }
        )
        original_name = normalize_optional_string(output["file"].get("filename")) or (
            normalize_optional_string(output["file"].get("name"))
        )
        assets.append(
            {
                "buffer": downloaded["buffer"],
                "mimeType": downloaded["mimeType"],
                "fileName": original_name
                or (
                    f"{params['capability']}-{asset_index}."
                    f"{_resolve_file_extension(mime_type=downloaded['mimeType'])}"
                ),
                "nodeId": output["nodeId"],
            }
        )

    return {
        "assets": assets,
        "model": provider_model,
        "promptId": prompt_id,
        "outputNodeIds": unique_strings([entry["nodeId"] for entry in output_files]),
    }
