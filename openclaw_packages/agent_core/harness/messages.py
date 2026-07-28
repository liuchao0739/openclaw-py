from __future__ import annotations

from typing import Any

from openclaw.llm.core import ImageContent, Message, TextContent

from ..agent_types import (
    AgentMessage,
)
from openclaw_packages.agent_core.harness.session.timestamps import parse_session_timestamp_ms, require_session_timestamp_ms

COMPACTION_SUMMARY_PREFIX = """The conversation history before this point was compacted into the following summary:

<summary>
"""

COMPACTION_SUMMARY_SUFFIX = """
</summary>"""

BRANCH_SUMMARY_PREFIX = """The following is a summary of a branch that this conversation came back from:

<summary>
"""

BRANCH_SUMMARY_SUFFIX = "</summary>"


def as_agent_message(message: AgentMessage) -> AgentMessage:
    return message


def _normalize_compaction_summary_timestamp(timestamp: int | str) -> int:
    if isinstance(timestamp, (int, float)):
        return int(timestamp)
    parsed = parse_session_timestamp_ms(timestamp)
    return parsed if parsed is not None else 0


def bash_execution_to_text(msg: dict[str, Any]) -> str:
    text = f"Ran `{msg.get('command', '')}`\n"
    output = msg.get("output")
    if output:
        text += f"```\n{output}\n```"
    else:
        text += "(no output)"
    if msg.get("cancelled"):
        text += "\n\n(command cancelled)"
    elif msg.get("exitCode") not in (None, 0):
        text += f"\n\nCommand exited with code {msg.get('exitCode')}"
    if msg.get("truncated") and msg.get("fullOutputPath"):
        text += f"\n\n[Output truncated. Full output: {msg.get('fullOutputPath')}]"
    return text


def create_branch_summary_message(
    summary: str,
    from_id: str,
    timestamp: str,
) -> AgentMessage:
    return {
        "role": "branchSummary",
        "summary": summary,
        "fromId": from_id,
        "timestamp": require_session_timestamp_ms(timestamp, "branch summary timestamp"),
    }


def create_compaction_summary_message(
    summary: str,
    tokens_before: int,
    timestamp: str,
) -> AgentMessage:
    return {
        "role": "compactionSummary",
        "summary": summary,
        "tokensBefore": tokens_before,
        "timestamp": require_session_timestamp_ms(timestamp, "compaction summary timestamp"),
    }


def create_custom_message(
    custom_type: str,
    content: str | list[Any],
    display: bool,
    details: Any,
    timestamp: str,
) -> AgentMessage:
    return {
        "role": "custom",
        "customType": custom_type,
        "content": content,
        "display": display,
        "details": details,
        "timestamp": require_session_timestamp_ms(timestamp, "custom message timestamp"),
    }


def convert_to_llm(messages: list[AgentMessage]) -> list[Message]:
    result: list[Message] = []
    for message in messages:
        role = message.get("role") if isinstance(message, dict) else getattr(message, "role", None)
        if role == "bashExecution":
            if message.get("excludeFromContext"):
                continue
            result.append({
                "role": "user",
                "content": [TextContent(text=bash_execution_to_text(message))],
                "timestamp": message.get("timestamp"),
            })
        elif role == "custom":
            content = message.get("content")
            if isinstance(content, str):
                content = [TextContent(text=content)]
            result.append({
                "role": "user",
                "content": content,
                "timestamp": message.get("timestamp"),
            })
        elif role == "branchSummary":
            result.append({
                "role": "user",
                "content": [
                    TextContent(
                        text=BRANCH_SUMMARY_PREFIX
                        + message.get("summary", "")
                        + BRANCH_SUMMARY_SUFFIX
                    )
                ],
                "timestamp": message.get("timestamp"),
            })
        elif role == "compactionSummary":
            result.append({
                "role": "user",
                "content": [
                    TextContent(
                        text=COMPACTION_SUMMARY_PREFIX
                        + message.get("summary", "")
                        + COMPACTION_SUMMARY_SUFFIX
                    )
                ],
                "timestamp": _normalize_compaction_summary_timestamp(
                    message.get("timestamp")
                ),
            })
        elif role in ("user", "assistant", "toolResult"):
            result.append(message)
    return result
