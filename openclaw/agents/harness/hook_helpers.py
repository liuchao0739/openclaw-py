"""Agent harness tool/message hook helpers.

Harnesses use this to dispatch after-tool-call and before-message-write hooks
while isolating hook failures from the runtime path.

The global hook runner is resolved lazily; when no plugin hook system is
registered these helpers become no-ops.
"""

from __future__ import annotations

import copy
import time
from typing import Any


def _get_global_hook_runner() -> Any | None:
    try:
        from openclaw.plugins.hook_runner_global import get_global_hook_runner
    except Exception:
        return None
    return get_global_hook_runner()


def _consume_adjusted_params_for_tool_call(tool_call_id: str, run_id: str | None) -> Any | None:
    try:
        from openclaw.agents.agent_tools_before_tool_call import (
            consume_adjusted_params_for_tool_call,
        )
    except Exception:
        return None
    return consume_adjusted_params_for_tool_call(tool_call_id, run_id)


async def run_agent_harness_after_tool_call_hook(params: dict[str, Any]) -> None:
    """Run best-effort after-tool-call hooks for a completed tool invocation."""
    adjusted_args = _consume_adjusted_params_for_tool_call(
        params.get("toolCallId", ""),
        params.get("runId"),
    )
    resolved_args = (
        adjusted_args
        if isinstance(adjusted_args, dict)
        else params.get("startArgs", {})
    )
    event_args = copy.deepcopy(resolved_args)
    hook_runner = _get_global_hook_runner()
    if hook_runner is None or not hook_runner.has_hooks("after_tool_call"):
        return
    try:
        await hook_runner.run_after_tool_call(
            {
                "toolName": params["toolName"],
                "params": event_args,
                **({"runId": params["runId"]} if params.get("runId") else {}),
                "toolCallId": params.get("toolCallId", ""),
                **({"result": params["result"]} if params.get("result") is not None else {}),
                **({"error": params["error"]} if params.get("error") else {}),
                **(
                    {"durationMs": int(time.time() * 1000) - params["startedAt"]}
                    if params.get("startedAt") is not None
                    else {}
                ),
            },
            {
                "toolName": params["toolName"],
                **({"agentId": params["agentId"]} if params.get("agentId") else {}),
                **({"sessionId": params["sessionId"]} if params.get("sessionId") else {}),
                **({"sessionKey": params["sessionKey"]} if params.get("sessionKey") else {}),
                **({"runId": params["runId"]} if params.get("runId") else {}),
                **({"channelId": params["channelId"]} if params.get("channelId") else {}),
                "toolCallId": params.get("toolCallId", ""),
            },
        )
    except Exception:
        pass


def run_agent_harness_before_message_write_hook(params: dict[str, Any]) -> dict[str, Any] | None:
    """Run before-message-write hooks and return the possibly rewritten message."""
    hook_runner = _get_global_hook_runner()
    if hook_runner is None or not hook_runner.has_hooks("before_message_write"):
        return params["message"]
    result = hook_runner.run_before_message_write(
        {"message": params["message"]},
        {
            **({"agentId": params["agentId"]} if params.get("agentId") else {}),
            **({"sessionKey": params["sessionKey"]} if params.get("sessionKey") else {}),
        },
    )
    if result is not None and result.get("block"):
        return None
    if result is not None:
        return result.get("message", params["message"])
    return params["message"]
