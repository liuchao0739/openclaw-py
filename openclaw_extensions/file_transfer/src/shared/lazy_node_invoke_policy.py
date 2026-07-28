from __future__ import annotations

from typing import Any, Callable

from openclaw.plugin_sdk.plugin_entry import (
    OpenClawPluginNodeInvokePolicy,
    OpenClawPluginNodeInvokePolicyContext,
    OpenClawPluginNodeInvokePolicyResult,
)
from openclaw_extensions.file_transfer.shared.node_invoke_policy_commands import (
    FILE_TRANSFER_NODE_INVOKE_COMMANDS,
)


async def _load_policy() -> OpenClawPluginNodeInvokePolicy:
    from openclaw_extensions.file_transfer.shared.node_invoke_policy import (
        create_file_transfer_node_invoke_policy,
    )
    return create_file_transfer_node_invoke_policy()


def create_lazy_file_transfer_node_invoke_policy(
    load_policy: Callable[[], Any] = _load_policy,
) -> OpenClawPluginNodeInvokePolicy:
    policy_future = None

    async def _handle(ctx: OpenClawPluginNodeInvokePolicyContext) -> OpenClawPluginNodeInvokePolicyResult:
        nonlocal policy_future
        try:
            if policy_future is None:
                policy_future = load_policy()
            policy = await policy_future
            return await policy["handle"](ctx)
        except Exception as error:
            message = str(error) if str(error) else repr(error)
            return {
                "ok": False,
                "code": "PLUGIN_POLICY_UNAVAILABLE",
                "message": f"file-transfer PLUGIN_POLICY_UNAVAILABLE: node.invoke policy unavailable: {message}",
                "unavailable": True,
            }

    return {
        "commands": list(FILE_TRANSFER_NODE_INVOKE_COMMANDS),
        "handle": _handle,
    }