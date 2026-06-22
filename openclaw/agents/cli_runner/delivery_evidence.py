"""Carries confirmed CLI messaging delivery across failed execution paths."""

from __future__ import annotations

from typing import Any, TypedDict

CLI_MESSAGING_DELIVERY_EVIDENCE_KEY = "cliMessagingDeliveryEvidence"


class CliMessagingDeliveryEvidence(TypedDict, total=False):
    didSendViaMessagingTool: bool
    didDeliverSourceReplyViaMessageTool: bool
    messagingToolSentTexts: list[str]
    messagingToolSentMediaUrls: list[str]
    messagingToolSentTargets: list[str]
    messagingToolSourceReplyPayloads: list[Any]


def _snapshot(output: CliMessagingDeliveryEvidence) -> CliMessagingDeliveryEvidence | None:
    if output.get("didSendViaMessagingTool") is not True:
        return None
    evidence: CliMessagingDeliveryEvidence = {"didSendViaMessagingTool": True}
    if output.get("didDeliverSourceReplyViaMessageTool"):
        evidence["didDeliverSourceReplyViaMessageTool"] = True
    texts = output.get("messagingToolSentTexts")
    if texts:
        evidence["messagingToolSentTexts"] = list(texts)
    urls = output.get("messagingToolSentMediaUrls")
    if urls:
        evidence["messagingToolSentMediaUrls"] = list(urls)
    targets = output.get("messagingToolSentTargets")
    if targets:
        evidence["messagingToolSentTargets"] = list(targets)
    payloads = output.get("messagingToolSourceReplyPayloads")
    if payloads:
        evidence["messagingToolSourceReplyPayloads"] = list(payloads)
    return evidence


def attach_cli_messaging_delivery_evidence(
    error: BaseException | Any,
    output: CliMessagingDeliveryEvidence,
) -> BaseException:
    evidence = _snapshot(output)
    if not evidence:
        if isinstance(error, BaseException):
            return error
        return RuntimeError(str(error))
    if isinstance(error, BaseException):
        setattr(error, CLI_MESSAGING_DELIVERY_EVIDENCE_KEY, evidence)
        return error
    wrapped = RuntimeError(str(error))
    setattr(wrapped, CLI_MESSAGING_DELIVERY_EVIDENCE_KEY, evidence)
    return wrapped


def get_cli_messaging_delivery_evidence(error: Any) -> CliMessagingDeliveryEvidence | None:
    if not isinstance(error, BaseException):
        return None
    evidence = getattr(error, CLI_MESSAGING_DELIVERY_EVIDENCE_KEY, None)
    if not isinstance(evidence, dict):
        return None
    return _snapshot(evidence)  # type: ignore[arg-type]