"""Bounded Codex app-server turns for media understanding and structured extraction."""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any

from openclaw_extensions.codex.src.app_server.config import resolve_codex_app_server_runtime_options

CODEX_BOUNDED_THREAD_CONFIG: dict[str, Any] = {
    "features.multi_agent": False,
    "features.apps": False,
    "features.plugins": False,
    "features.image_generation": False,
    "features.standalone_web_search": False,
    "web_search": "disabled",
}
CODEX_PRIVATE_BOUNDED_THREAD_CONFIG: dict[str, Any] = {
    "features.hooks": False,
    "notify": [],
}
CODEX_CODE_MODE_DISABLED_THREAD_CONFIG: dict[str, Any] = {
    "features.code_mode": False,
    "features.code_mode_only": False,
}
CODEX_PRIVATE_STDIO_ARGS = ["app-server", "--listen", "stdio://"]


def _merge_thread_configs(*configs: dict[str, Any] | None) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for config in configs:
        if config:
            merged.update(config)
    return merged


def _resolve_bounded_thread_config(params: dict[str, Any], workspace: dict[str, Any]) -> dict[str, Any]:
    bounded = _merge_thread_configs(CODEX_BOUNDED_THREAD_CONFIG, params.get("threadConfig"))
    if workspace.get("codexHome"):
        bounded = _merge_thread_configs(bounded, CODEX_PRIVATE_BOUNDED_THREAD_CONFIG)
    return _merge_thread_configs(
        bounded,
        CODEX_CODE_MODE_DISABLED_THREAD_CONFIG,
    )


def _build_codex_runtime_thread_config(config: dict[str, Any] | None, options: dict[str, Any] | None = None) -> dict[str, Any]:
    options = options or {}
    if options.get("nativeCodeModeEnabled") is False:
        return _merge_thread_configs(config, CODEX_CODE_MODE_DISABLED_THREAD_CONFIG)
    return dict(config or {})


def _read_string(record: dict[str, Any], key: str) -> str | None:
    value = record.get(key)
    return value if isinstance(value, str) else None


def _is_terminal_turn(turn: dict[str, Any]) -> bool:
    status = turn.get("status")
    return status in {"completed", "failed", "cancelled"}


def _collect_assistant_text_from_items(items: list[dict[str, Any]] | None) -> str:
    texts = [
        str(item.get("text") or "").strip()
        for item in items or []
        if item.get("type") == "agentMessage" and str(item.get("text") or "").strip()
    ]
    return "\n\n".join(texts).strip()


class _BoundedTurnCollector:
    def __init__(self, thread_id: str, task_label: str) -> None:
        self._thread_id = thread_id
        self._task_label = task_label
        self._turn_id: str | None = None
        self._completed_turn: dict[str, Any] | None = None
        self._prompt_error: str | None = None
        self._pending: list[dict[str, Any]] = []
        self._completed_items: dict[str, dict[str, Any]] = {}
        self._assistant_text_by_item: dict[str, str] = {}
        self._assistant_item_order: list[str] = []
        self._completion = asyncio.Event()

    def _remember_assistant_text(self, item_id: str, text: str) -> None:
        if not text:
            return
        if item_id not in self._assistant_text_by_item:
            self._assistant_item_order.append(item_id)
        self._assistant_text_by_item[item_id] = text

    def handle_notification(self, notification: dict[str, Any]) -> None:
        params = notification.get("params")
        if not isinstance(params, dict) or params.get("threadId") != self._thread_id:
            return
        if not self._turn_id:
            self._pending.append(notification)
            return
        notification_turn_id = params.get("turnId") or params.get("turn_id")
        if notification_turn_id != self._turn_id:
            return
        method = notification.get("method")
        if method == "item/completed":
            item = params.get("item")
            if isinstance(item, dict):
                self._completed_items[item["id"]] = item
                if item.get("type") == "agentMessage" and isinstance(item.get("text"), str):
                    self._remember_assistant_text(item["id"], item["text"])
            return
        if method == "item/agentMessage/delta":
            item_id = _read_string(params, "itemId") or _read_string(params, "id") or "assistant"
            delta = _read_string(params, "delta") or ""
            self._remember_assistant_text(item_id, f"{self._assistant_text_by_item.get(item_id, '')}{delta}")
            return
        if method == "turn/completed":
            turn = params.get("turn")
            if isinstance(turn, dict):
                self._completed_turn = turn
            self._completion.set()
            return
        if method == "error":
            error = params.get("error")
            message = error.get("message") if isinstance(error, dict) else None
            self._prompt_error = message or f"codex app-server {self._task_label} turn failed"
            self._completion.set()

    async def collect(self, started_turn: dict[str, Any], *, timeout_ms: int) -> dict[str, Any]:
        self._turn_id = started_turn["id"]
        if _is_terminal_turn(started_turn):
            self._completed_turn = started_turn
        pending = list(self._pending)
        self._pending.clear()
        for notification in pending:
            self.handle_notification(notification)
        if not self._completed_turn and not self._prompt_error:
            try:
                await asyncio.wait_for(self._completion.wait(), timeout=timeout_ms / 1000)
            except TimeoutError as exc:
                raise RuntimeError(f"codex app-server {self._task_label} turn timed out") from exc
        if self._prompt_error:
            raise RuntimeError(self._prompt_error)
        if self._completed_turn and self._completed_turn.get("status") == "failed":
            error = self._completed_turn.get("error")
            message = error.get("message") if isinstance(error, dict) else None
            raise RuntimeError(message or f"codex app-server {self._task_label} turn failed")
        items_map = dict(self._completed_items)
        for item in self._completed_turn.get("items") if self._completed_turn else []:
            if isinstance(item, dict):
                items_map[item["id"]] = item
        items = list(items_map.values())
        item_text = _collect_assistant_text_from_items(items)
        delta_text = "\n\n".join(
            text
            for item_id in self._assistant_item_order
            if (text := self._assistant_text_by_item.get(item_id, "").strip())
        ).strip()
        text = (item_text or delta_text).strip()
        if not text:
            raise RuntimeError(f"Codex app-server {self._task_label} turn returned no text.")
        return {"text": text, "items": items}


def _create_bounded_approval_handler(task_label: str):
    def handler(request: dict[str, Any]) -> Any:
        method = request.get("method")
        if method in {"item/commandExecution/requestApproval", "item/fileChange/requestApproval"}:
            return {
                "decision": "decline",
                "reason": f"OpenClaw Codex {task_label} does not grant tool or file approvals.",
            }
        if method == "item/permissions/requestApproval":
            return {"permissions": {}, "scope": "turn"}
        if isinstance(method, str) and "requestApproval" in method:
            return {
                "decision": "decline",
                "reason": f"OpenClaw Codex {task_label} does not grant native approvals.",
            }
        if method == "mcpServer/elicitation/request":
            return {"action": "decline"}
        return None

    return handler


async def _resolve_codex_bounded_turn_model(
    *,
    client: Any,
    selection: dict[str, Any],
    required_modalities: list[str],
    timeout_ms: int,
) -> str:
    result = await client.request(
        "model/list",
        {"limit": None, "cursor": None, "includeHidden": False},
        timeoutMs=min(timeout_ms, 5000),
    )
    data = result.get("data") if isinstance(result, dict) else []
    models = data if isinstance(data, list) else []
    if selection.get("mode") == "live-default":
        supported = [
            entry
            for entry in models
            if isinstance(entry, dict)
            and all(modality in (entry.get("inputModalities") or []) for modality in required_modalities)
        ]
        selected = next((entry for entry in supported if entry.get("isDefault")), None) or (
            supported[0] if supported else None
        )
        if not selected:
            raise RuntimeError(
                f"Codex app-server has no model supporting {' and '.join(required_modalities)} input."
            )
        return str(selected.get("model") or selected.get("id"))
    model = str(selection.get("id") or "").strip()
    match = next(
        (
            entry
            for entry in models
            if isinstance(entry, dict) and (entry.get("model") == model or entry.get("id") == model)
        ),
        None,
    )
    if not match:
        raise RuntimeError(f"Codex app-server model not found: {model}")
    input_modalities = match.get("inputModalities") or []
    if "image" in required_modalities and "image" not in input_modalities:
        raise RuntimeError(f"Codex app-server model does not support images: {model}")
    if "text" in required_modalities and "text" not in input_modalities:
        raise RuntimeError(f"Codex app-server model does not support text: {model}")
    return model


async def _run_bounded_codex_app_server_turn_in_workspace(
    params: dict[str, Any],
    app_server: dict[str, Any],
    workspace: dict[str, Any],
) -> dict[str, Any]:
    timeout_ms = int(params.get("timeoutMs") or 100)
    timeout_ms = max(timeout_ms, 100)
    agent_dir = str(params.get("agentDir") or "").strip() or None
    start_options = app_server["start"]
    owns_client = not params.get("options", {}).get("clientFactory")
    client_factory = params.get("options", {}).get("clientFactory")
    if client_factory:
        client = await client_factory(
            start_options,
            params.get("profile"),
            agent_dir,
            params.get("config"),
            {"timeoutMs": timeout_ms},
        )
    else:
        from openclaw_extensions.codex.src.app_server.shared_client import (
            create_isolated_codex_app_server_client,
        )

        client = await create_isolated_codex_app_server_client(
            startOptions=start_options,
            timeoutMs=timeout_ms,
            authProfileId=params.get("profile"),
            agentDir=agent_dir,
            authProfileStore=params.get("authProfileStore"),
            config=params.get("config"),
        )
    try:
        model = await _resolve_codex_bounded_turn_model(
            client=client,
            selection=params["model"],
            required_modalities=list(params.get("requiredModalities") or []),
            timeout_ms=timeout_ms,
        )
        thread_response = await client.request(
            "thread/start",
            {
                "model": model,
                "modelProvider": "openai",
                "cwd": workspace["cwd"],
                "approvalPolicy": "on-request",
                "sandbox": "read-only",
                "serviceName": "OpenClaw",
                "developerInstructions": params["developerInstructions"],
                "config": _build_codex_runtime_thread_config(
                    _resolve_bounded_thread_config(params, workspace),
                    {"nativeCodeModeEnabled": False},
                ),
                "environments": [],
                "dynamicTools": [],
                "experimentalRawEvents": True,
                "persistExtendedHistory": False,
                "ephemeral": True,
            },
            timeoutMs=timeout_ms,
        )
        thread = thread_response.get("thread") if isinstance(thread_response, dict) else None
        if not isinstance(thread, dict):
            raise TypeError("Codex app-server thread/start returned invalid response")
        collector = _BoundedTurnCollector(thread["id"], params["taskLabel"])
        cleanup_notification = client.add_notification_handler(collector.handle_notification)
        cleanup_request = client.add_request_handler(_create_bounded_approval_handler(params["taskLabel"]))
        try:
            turn_response = await client.request(
                "turn/start",
                {
                    "threadId": thread["id"],
                    "input": params["input"],
                    "cwd": workspace["cwd"],
                    "approvalPolicy": "on-request",
                    "model": model,
                    "effort": "low",
                },
                timeoutMs=timeout_ms,
            )
            turn = turn_response.get("turn") if isinstance(turn_response, dict) else None
            if not isinstance(turn, dict):
                raise TypeError("Codex app-server turn/start returned invalid response")
            collected = await collector.collect(turn, timeout_ms=timeout_ms)
            return {**collected, "model": model}
        finally:
            cleanup_request()
            cleanup_notification()
    finally:
        if owns_client:
            client.close()


async def run_bounded_codex_app_server_turn(params: dict[str, Any]) -> dict[str, Any]:
    app_server = resolve_codex_app_server_runtime_options({"pluginConfig": params.get("options", {}).get("pluginConfig")})
    if params.get("isolation") == "configured-transport":
        cwd = str(params.get("agentDir") or "").strip() or os.getcwd()
        return await _run_bounded_codex_app_server_turn_in_workspace(params, app_server, {"cwd": cwd})
    if app_server["start"].get("transport") != "stdio":
        raise RuntimeError("Bounded Codex turns require stdio transport so native tools can be isolated.")
    with tempfile.TemporaryDirectory(prefix="codex-bounded-turn-") as workspace_dir:
        codex_home = str(Path(workspace_dir) / "codex-home")
        cwd = str(Path(workspace_dir) / "workspace")
        Path(codex_home).mkdir(parents=True, exist_ok=True)
        Path(cwd).mkdir(parents=True, exist_ok=True)
        return await _run_bounded_codex_app_server_turn_in_workspace(
            params,
            app_server,
            {"codexHome": codex_home, "cwd": cwd},
        )
