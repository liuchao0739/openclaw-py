import json
import os
import base64
import time
from typing import Dict, Optional, Any

from .api import (
    PAIRING_SETUP_BOOTSTRAP_PROFILE,
    approveDevicePairing,
    clearDeviceBootstrapTokens,
    issueDeviceBootstrapToken,
    listDevicePairing,
    revokeDeviceBootstrapToken,
    resolveGatewayBindUrl,
    resolveGatewayPort,
    resolveScheme,
    normalizeUrl,
    validateMobilePairingUrl,
    pickLanIPv4,
    pickTailnetIPv4,
    resolvePreferredOpenClawTmpDir,
    normalize_optional_string,
    normalize_lowercase_string_or_empty,
)
from .qr_image import renderQrPngDataUrl, writeQrPngTempFile
from .notify import formatPendingRequests, handleNotifyCommand, armPairNotifyOnce, createPairingNotifierService
from .pair_command_auth import (
    buildMissingPairingScopeReply,
    buildMissingSetupHandoffScopeReply,
    resolvePairingCommandAuthState,
)
from .pair_command_approve import approvePendingPairingRequest, selectPendingApprovalRequest


QR_CHANNEL_SENDERS = {
    "telegram": {
        "createOpts": lambda ctx, qr_file_path, media_local_roots, account_id: {
            "mediaUrl": qr_file_path,
            "mediaLocalRoots": media_local_roots,
            **({"threadId": ctx.get("messageThreadId")} if ctx.get("messageThreadId") is not None else {}),
            **({"accountId": account_id} if account_id else {}),
        }
    },
    "discord": {
        "createOpts": lambda ctx, qr_file_path, media_local_roots, account_id: {
            "mediaUrl": qr_file_path,
            "mediaLocalRoots": media_local_roots,
            **({"accountId": account_id} if account_id else {}),
        }
    },
    "slack": {
        "createOpts": lambda ctx, qr_file_path, media_local_roots, account_id: {
            "mediaUrl": qr_file_path,
            "mediaLocalRoots": media_local_roots,
            **({"threadId": str(ctx.get("messageThreadId"))} if ctx.get("messageThreadId") is not None else {}),
            **({"accountId": account_id} if account_id else {}),
        }
    },
    "signal": {
        "createOpts": lambda ctx, qr_file_path, media_local_roots, account_id: {
            "mediaUrl": qr_file_path,
            "mediaLocalRoots": media_local_roots,
            **({"accountId": account_id} if account_id else {}),
        }
    },
    "imessage": {
        "createOpts": lambda ctx, qr_file_path, media_local_roots, account_id: {
            "mediaUrl": qr_file_path,
            "mediaLocalRoots": media_local_roots,
            **({"accountId": account_id} if account_id else {}),
        }
    },
    "whatsapp": {
        "createOpts": lambda ctx, qr_file_path, media_local_roots, account_id: {
            "verbose": False,
            "mediaUrl": qr_file_path,
            "mediaLocalRoots": media_local_roots,
            **({"accountId": account_id} if account_id else {}),
        }
    },
}


def formatDurationMinutes(expiresAtMs: int) -> str:
    msRemaining = max(0, expiresAtMs - int(time.time() * 1000))
    minutes = max(1, (msRemaining + 59999) // 60000)
    return f"{minutes} minute{'s' if minutes != 1 else ''}"


def pickFirstDefined(candidates) -> Optional[str]:
    for value in candidates:
        trimmed = normalize_optional_string(value)
        if trimmed:
            return trimmed
    return None


def resolveAuthLabel(cfg: Dict) -> Dict:
    mode = cfg.get("gateway", {}).get("auth", {}).get("mode")
    token = pickFirstDefined([os.environ.get("OPENCLAW_GATEWAY_TOKEN"), cfg.get("gateway", {}).get("auth", {}).get("token")])
    password = pickFirstDefined([os.environ.get("OPENCLAW_GATEWAY_PASSWORD"), cfg.get("gateway", {}).get("auth", {}).get("password")])

    if mode in ("token", "password"):
        if mode == "token":
            return {"label": "token"} if token else {"error": "Gateway auth is set to token, but no token is configured."}
        return {"label": "password"} if password else {"error": "Gateway auth is set to password, but no password is configured."}

    if token:
        return {"label": "token"}
    if password:
        return {"label": "password"}
    return {"error": "Gateway auth is not configured (no token or password)."}


async def resolveGatewayUrl(api) -> Dict:
    cfg = api.config
    pluginCfg = api.pluginConfig or {}
    scheme = resolveScheme(cfg)
    port = resolveGatewayPort(cfg)

    configuredPublicUrl = normalize_optional_string(pluginCfg.get("publicUrl"))
    if configuredPublicUrl:
        url = normalizeUrl(configuredPublicUrl, scheme)
        if url:
            return {"url": url, "source": "plugins.entries.device-pair.config.publicUrl"}
        return {"error": "Configured publicUrl is invalid."}

    configuredRemoteUrl = normalize_optional_string(cfg.get("gateway", {}).get("remote", {}).get("url"))
    remoteUrl = normalizeUrl(configuredRemoteUrl, scheme) if configuredRemoteUrl else None
    if configuredRemoteUrl and not remoteUrl:
        return {"error": "Configured gateway.remote.url is invalid."}

    tailscaleMode = cfg.get("gateway", {}).get("tailscale", {}).get("mode", "off")
    if tailscaleMode in ("serve", "funnel"):
        host = pickTailnetIPv4()
        if not host:
            return {"error": "Tailscale Serve is enabled, but MagicDNS could not be resolved."}
        return {"url": f"wss://{host}", "source": f"gateway.tailscale.mode={tailscaleMode}"}

    if remoteUrl:
        return {"url": remoteUrl, "source": "gateway.remote.url"}

    bindResult = resolveGatewayBindUrl({
        "bind": cfg.get("gateway", {}).get("bind"),
        "customBindHost": cfg.get("gateway", {}).get("customBindHost"),
        "scheme": scheme,
        "port": port,
        "pickTailnetHost": pickTailnetIPv4,
        "pickLanHost": pickLanIPv4,
    })
    if bindResult:
        return bindResult

    return {
        "error": "Gateway is only bound to loopback. Set gateway.bind=lan, enable tailscale serve, or configure plugins.entries.device-pair.config.publicUrl."
    }


async def resolveMobilePairingGatewayUrl(api) -> Dict:
    result = await resolveGatewayUrl(api)
    if not result.get("url"):
        return result
    mobilePairingUrlError = validateMobilePairingUrl(result["url"], result.get("source"))
    if mobilePairingUrlError:
        return {"error": mobilePairingUrlError}
    return result


def encodeSetupCode(payload: Dict) -> str:
    json_str = json.dumps(payload)
    base64_str = base64.b64encode(json_str.encode("utf8")).decode("utf8")
    return base64_str.replace("+", "-").replace("/", "_").rstrip("=")


def buildPairingFlowLines(stepTwo: str) -> list:
    return [
        "1) Open the iOS app → Settings → Gateway",
        f"2) {stepTwo}",
        "3) Back here, run /pair approve",
        "4) If this code leaks or you are done, run /pair cleanup",
    ]


def buildSecurityNoticeLines(params: Dict) -> list:
    cleanupCommand = "`/pair cleanup`" if params.get("markdown") else "/pair cleanup"
    securityPrefix = "- " if params.get("markdown") else ""
    importantLine = (
        f"**Important:** Run {cleanupCommand} after pairing finishes."
        if params.get("markdown")
        else f"IMPORTANT: After pairing finishes, run {cleanupCommand}."
    )
    return [
        f"{securityPrefix}Security: single-use bootstrap token",
        f"{securityPrefix}Expires: {formatDurationMinutes(params['expiresAtMs'])}",
        "",
        importantLine,
        f"If this {params['kind']} leaks, run {cleanupCommand} immediately.",
    ]


def buildQrFollowUpLines(autoNotifyArmed: bool) -> list:
    if autoNotifyArmed:
        return [
            "After scanning, wait here for the pairing request ping.",
            "I'll auto-ping here when the pairing request arrives, then auto-disable.",
            "If the ping does not arrive, run `/pair approve latest` manually.",
        ]
    return ["After scanning, run `/pair approve` to complete pairing."]


def formatSetupReply(payload: Dict, authLabel: str) -> str:
    setupCode = encodeSetupCode(payload)
    return "\n".join([
        "Pairing setup code generated.",
        "",
        *buildPairingFlowLines("Paste the setup code below and tap Connect"),
        "",
        "Setup code:",
        setupCode,
        "",
        f"Gateway: {payload['url']}",
        f"Auth: {authLabel}",
        *buildSecurityNoticeLines({
            "kind": "setup code",
            "expiresAtMs": payload["expiresAtMs"],
        }),
    ])


def formatSetupInstructions(expiresAtMs: int) -> str:
    return "\n".join([
        "Pairing setup code generated.",
        "",
        *buildPairingFlowLines("Paste the setup code from my next message and tap Connect"),
        "",
        *buildSecurityNoticeLines({
            "kind": "setup code",
            "expiresAtMs": expiresAtMs,
        }),
    ])


def buildQrInfoLines(params: Dict) -> list:
    return [
        f"Gateway: {params['payload']['url']}",
        f"Auth: {params['authLabel']}",
        *buildSecurityNoticeLines({
            "kind": "QR code",
            "expiresAtMs": params["expiresAtMs"],
        }),
        "",
        *buildQrFollowUpLines(params["autoNotifyArmed"]),
        "",
        "If your camera still won't lock on, run `/pair` for a pasteable setup code.",
    ]


def formatQrInfoMarkdown(params: Dict) -> str:
    return "\n".join([
        f"- Gateway: {params['payload']['url']}",
        f"- Auth: {params['authLabel']}",
        *buildSecurityNoticeLines({
            "kind": "QR code",
            "expiresAtMs": params["expiresAtMs"],
            "markdown": True,
        }),
        "",
        *buildQrFollowUpLines(params["autoNotifyArmed"]),
        "",
        "If your camera still won't lock on, run `/pair` for a pasteable setup code.",
    ])


def canSendQrPngToChannel(channel: str) -> bool:
    return channel in QR_CHANNEL_SENDERS


def resolveQrReplyTarget(ctx: Dict) -> str:
    if ctx.get("channel") == "discord":
        senderId = normalize_optional_string(ctx.get("senderId")) or ""
        if senderId:
            if senderId.startswith("user:") or senderId.startswith("channel:"):
                return senderId
            return f"user:{senderId}"
    return (
        normalize_optional_string(ctx.get("senderId"))
        or normalize_optional_string(ctx.get("from"))
        or normalize_optional_string(ctx.get("to"))
        or ""
    )


async def issueSetupPayload(url: str) -> Dict:
    issuedBootstrap = await issueDeviceBootstrapToken({
        "profile": PAIRING_SETUP_BOOTSTRAP_PROFILE,
    })
    return {
        "url": url,
        "bootstrapToken": issuedBootstrap["token"],
        "expiresAtMs": issuedBootstrap["expiresAtMs"],
    }


async def sendQrPngToSupportedChannel(params: Dict) -> bool:
    mediaLocalRoots = [os.path.dirname(params["qrFilePath"])]
    accountId = normalize_optional_string(params["ctx"].get("accountId")) or None
    sender = QR_CHANNEL_SENDERS.get(params["ctx"]["channel"])
    if not sender:
        return False

    api = params["api"]
    adapter = await api.runtime.channel.outbound.loadAdapter(params["ctx"]["channel"])
    send = getattr(adapter, "sendMedia", None) if adapter else None
    if not send:
        return False

    await send({
        "cfg": api.config,
        "to": params["target"],
        "text": params["caption"],
        **sender["createOpts"](params["ctx"], params["qrFilePath"], mediaLocalRoots, accountId),
    })
    return True


async def handlePairCommand(api, ctx):
    args = normalize_optional_string(ctx.get("args")) or ""
    tokens = args.split()
    action = normalize_lowercase_string_or_empty(tokens[0] if tokens else "")
    gatewayClientScopes = ctx.get("gatewayClientScopes") if isinstance(ctx.get("gatewayClientScopes"), list) else None

    authState = resolvePairingCommandAuthState({
        "channel": ctx.get("channel"),
        "gatewayClientScopes": gatewayClientScopes,
        "senderIsOwner": ctx.get("senderIsOwner"),
    })

    api.logger.info(f"device-pair: /pair invoked channel={ctx.get('channel')} sender={ctx.get('senderId') or 'unknown'} action={action or 'new'}")

    if authState["isMissingPairingPrivilege"]:
        return buildMissingPairingScopeReply()

    if action in ("status", "pending"):
        list_result = await listDevicePairing()
        return {"text": formatPendingRequests(list_result.get("pending", []))}

    if action == "notify":
        notifyAction = normalize_lowercase_string_or_empty(tokens[1]) if len(tokens) > 1 else "status"
        return await handleNotifyCommand({
            "api": api,
            "ctx": ctx,
            "action": notifyAction,
        })

    if action == "approve":
        list_result = await listDevicePairing()
        requested = normalize_optional_string(tokens[1]) if len(tokens) > 1 else None
        selected = selectPendingApprovalRequest({
            "pending": list_result.get("pending", []),
            "requested": requested,
        })
        if selected.get("reply"):
            return selected["reply"]
        pending = selected.get("pending")
        if not pending:
            return {"text": "Pairing request not found."}
        return await approvePendingPairingRequest({
            "requestId": pending.get("requestId"),
            "callerScopes": authState.get("approvalCallerScopes"),
        })

    if action in ("cleanup", "clear", "revoke"):
        cleared = await clearDeviceBootstrapTokens()
        removed = cleared.get("removed", 0)
        return {
            "text": (
                f"Invalidated {removed} unused setup code{'s' if removed != 1 else ''}."
                if removed > 0
                else "No unused setup codes were active."
            )
        }

    if authState["isMissingSetupHandoffPrivilege"]:
        return buildMissingSetupHandoffScopeReply()

    authLabelResult = resolveAuthLabel(api.config)
    if authLabelResult.get("error"):
        return {"text": f"Error: {authLabelResult['error']}"}

    urlResult = await resolveMobilePairingGatewayUrl(api)
    if not urlResult.get("url"):
        return {"text": f"Error: {urlResult.get('error') or 'Gateway URL unavailable.'}"}

    authLabel = authLabelResult.get("label") or "auth"

    if action == "qr":
        channel = ctx.get("channel")
        target = resolveQrReplyTarget(ctx)
        autoNotifyArmed = False

        if channel == "telegram" and target:
            try:
                autoNotifyArmed = await armPairNotifyOnce({"api": api, "ctx": ctx})
            except Exception as err:
                api.logger.warn(f"device-pair: failed to arm one-shot pairing notify ({err})")

        payload = await issueSetupPayload(urlResult["url"])
        setupCode = encodeSetupCode(payload)

        infoLines = buildQrInfoLines({
            "payload": payload,
            "authLabel": authLabel,
            "autoNotifyArmed": autoNotifyArmed,
            "expiresAtMs": payload["expiresAtMs"],
        })

        if target and canSendQrPngToChannel(channel):
            qrFilePath = None
            try:
                qrFilePath = (
                    await writeQrPngTempFile(setupCode, {
                        "tmpRoot": resolvePreferredOpenClawTmpDir(),
                        "dirPrefix": "device-pair-qr-",
                        "fileName": "pair-qr.png",
                    })
                )["filePath"]
                sent = await sendQrPngToSupportedChannel({
                    "api": api,
                    "ctx": ctx,
                    "target": target,
                    "caption": "\n".join(["Scan this QR code with the OpenClaw iOS app:", "", *infoLines]),
                    "qrFilePath": qrFilePath,
                })
                if sent:
                    return {
                        "text": (
                            f"QR code sent above.\n"
                            f"Expires: {formatDurationMinutes(payload['expiresAtMs'])}\n"
                            "IMPORTANT: Run /pair cleanup after pairing finishes."
                        )
                    }
            except Exception as err:
                api.logger.warn(f"device-pair: QR image send failed channel={channel}, falling back ({err})")
                await revokeDeviceBootstrapToken({"token": payload["bootstrapToken"]})
                payload = await issueSetupPayload(urlResult["url"])
                setupCode = encodeSetupCode(payload)
            finally:
                if qrFilePath:
                    try:
                        os.remove(qrFilePath)
                        os.rmdir(os.path.dirname(qrFilePath))
                    except Exception:
                        pass

        api.logger.info(f"device-pair: QR fallback channel={channel} target={target}")

        if channel == "webchat":
            try:
                qrDataUrl = await renderQrPngDataUrl(setupCode)
            except Exception as err:
                api.logger.warn(f"device-pair: webchat QR render failed, falling back ({err})")
                await revokeDeviceBootstrapToken({"token": payload["bootstrapToken"]})
                payload = await issueSetupPayload(urlResult["url"])
                return {
                    "text": (
                        "QR image delivery is not available on this channel right now, so I generated a pasteable setup code instead.\n\n"
                        + formatSetupReply(payload, authLabel)
                    )
                }
            return {
                "text": "\n".join([
                    "Scan this QR code with the OpenClaw iOS app:",
                    "",
                    formatQrInfoMarkdown({
                        "payload": payload,
                        "authLabel": authLabel,
                        "autoNotifyArmed": autoNotifyArmed,
                        "expiresAtMs": payload["expiresAtMs"],
                    }),
                ]),
                "mediaUrl": qrDataUrl,
                "sensitiveMedia": True,
            }

        return {
            "text": (
                "QR image delivery is not available on this channel, so I generated a pasteable setup code instead.\n\n"
                + formatSetupReply(payload, authLabel)
            )
        }

    channel = ctx.get("channel")
    target = (
        normalize_optional_string(ctx.get("senderId"))
        or normalize_optional_string(ctx.get("from"))
        or normalize_optional_string(ctx.get("to"))
        or ""
    )
    payload = await issueSetupPayload(urlResult["url"])

    if channel == "telegram" and target:
        try:
            adapter = await api.runtime.channel.outbound.loadAdapter("telegram")
            send = getattr(adapter, "sendText", None) if adapter else None
            if not send:
                raise RuntimeError("telegram runtime unavailable")

            await send({
                "cfg": api.config,
                "to": target,
                "text": formatSetupInstructions(payload["expiresAtMs"]),
                **({"threadId": ctx.get("messageThreadId")} if ctx.get("messageThreadId") is not None else {}),
                **({"accountId": ctx.get("accountId")} if ctx.get("accountId") else {}),
            })
            api.logger.info(f"device-pair: telegram split send ok target={target} account={ctx.get('accountId') or 'none'} thread={ctx.get('messageThreadId') or 'none'}")
            return {"text": encodeSetupCode(payload)}
        except Exception as err:
            api.logger.warn(f"device-pair: telegram split send failed, falling back to single message ({err})")

    return {"text": formatSetupReply(payload, authLabel)}


def load_device_pair_extension():
    def register(api):
        notifier_service = createPairingNotifierService(api)

        async def start_service(ctx=None):
            await notifier_service["start"](ctx)

        async def stop_service(ctx=None):
            await notifier_service["stop"](ctx)

        async def command_handler(ctx):
            return await handlePairCommand(api, ctx)

        return {
            "services": [{
                "id": "device-pair-notifier",
                "start": start_service,
                "stop": stop_service,
            }],
            "commands": [{
                "name": "pair",
                "description": "Generate setup codes and approve device pairing requests.",
                "acceptsArgs": True,
                "requiredScopes": ["operator.pairing"],
                "handler": command_handler,
            }],
        }

    return {
        "id": "device-pair",
        "name": "Device Pair",
        "description": "QR/bootstrap pairing helpers for OpenClaw devices",
        "register": register,
    }

__all__ = ["load_device_pair_extension"]