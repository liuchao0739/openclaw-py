from __future__ import annotations

from openclaw.plugin_sdk.approval_handler_adapter_runtime import (
    CHANNEL_APPROVAL_NATIVE_RUNTIME_CONTEXT_CAPABILITY,
)
from openclaw.plugin_sdk.channel_outbound import (
    create_account_status_sink,
    run_passive_account_lifecycle,
)
from openclaw.plugin_sdk.channel_runtime_context import register_channel_runtime_context
from openclaw.plugin_sdk.lazy_runtime import create_lazy_runtime_named_export
from openclaw_extensions.googlechat.src.accounts import ResolvedGoogleChatAccount
from openclaw_extensions.googlechat.src.approval_native import (
    is_google_chat_native_approval_client_enabled,
)
from openclaw_extensions.googlechat.src.monitor_types import GoogleChatRuntimeEnv

load_google_chat_channel_runtime = create_lazy_runtime_named_export(
    lambda: __import__(
        "openclaw_extensions.googlechat.src.channel_runtime",
        fromlist=["google_chat_channel_runtime"],
    ),
    "googleChatChannelRuntime",
)


async def start_google_chat_gateway_account(ctx: dict) -> None:
    account = ctx["account"]
    status_sink = create_account_status_sink({
        "accountId": account.account_id,
        "setStatus": ctx["setStatus"],
    })
    log_fn = ctx.get("log", {}).get("info")
    if log_fn:
        log_fn(f"[{account.account_id}] starting Google Chat webhook")

    runtime_data = await load_google_chat_channel_runtime()
    resolve_fn = runtime_data["resolveGoogleChatWebhookPath"]
    start_fn = runtime_data["startGoogleChatMonitor"]

    status_sink({
        "running": True,
        "lastStartAt": __import__("time").time() * 1000,
        "webhookPath": resolve_fn({"account": account}),
        "audienceType": account.config.get("audienceType"),
        "audience": account.config.get("audience"),
    })

    stopped = False

    def mark_stopped():
        nonlocal stopped
        if stopped:
            return
        stopped = True
        status_sink({
            "running": False,
            "lastStopAt": __import__("time").time() * 1000,
        })

    if is_google_chat_native_approval_client_enabled({
        "cfg": ctx["cfg"],
        "accountId": account.account_id,
    }):
        register_channel_runtime_context({
            "channelRuntime": ctx.get("channelRuntime"),
            "channelId": "googlechat",
            "accountId": account.account_id,
            "capability": CHANNEL_APPROVAL_NATIVE_RUNTIME_CONTEXT_CAPABILITY,
            "context": {"account": account},
            "abortSignal": ctx["abortSignal"],
        })

    try:
        await run_passive_account_lifecycle({
            "abortSignal": ctx["abortSignal"],
            "start": lambda: start_fn({
                "account": account,
                "config": ctx["cfg"],
                "runtime": ctx["runtime"],
                "abortSignal": ctx["abortSignal"],
                "webhookPath": account.config.get("webhookPath"),
                "webhookUrl": account.config.get("webhookUrl"),
                "statusSink": status_sink,
            }),
            "stop": lambda unregister: (unregister() if unregister else None),
            "onStop": mark_stopped,
        })
    except Exception as error:
        mark_stopped()
        raise error


__all__ = ["start_google_chat_gateway_account"]