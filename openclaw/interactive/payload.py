from __future__ import annotations

from typing import Any, Literal, Mapping, TypedDict

from openclaw_packages.normalization_core.record_coerce import as_optional_record
from openclaw_packages.normalization_core.string_coerce import (
    normalize_optional_lowercase_string,
    normalize_optional_string,
)

InteractiveButtonStyle = Literal["primary", "secondary", "success", "danger"]
MessagePresentationTone = Literal["info", "success", "warning", "danger", "neutral"]


class MessagePresentationAction(TypedDict, total=False):
    type: str
    command: str
    value: str


class MessagePresentationButton(TypedDict, total=False):
    label: str
    action: MessagePresentationAction
    value: str
    url: str
    webApp: dict[str, str]
    web_app: dict[str, str]
    priority: int
    disabled: bool
    reusable: bool
    style: str


class MessagePresentationOption(TypedDict, total=False):
    label: str
    action: MessagePresentationAction
    value: str


class InteractiveReplyTextBlock(TypedDict):
    type: Literal["text"]
    text: str


class _InteractiveReplyButtonsBlock(TypedDict):
    type: Literal["buttons"]
    buttons: list[MessagePresentationButton]


class InteractiveReplySelectBlock(TypedDict, total=False):
    type: Literal["select"]
    placeholder: str
    options: list[MessagePresentationOption]


InteractiveReplyBlock = InteractiveReplyTextBlock | _InteractiveReplyButtonsBlock | InteractiveReplySelectBlock


class InteractiveReply(TypedDict):
    blocks: list[InteractiveReplyBlock]


class MessagePresentationTextBlock(TypedDict):
    type: Literal["text"]
    text: str


class MessagePresentationContextBlock(TypedDict):
    type: Literal["context"]
    text: str


class MessagePresentationDividerBlock(TypedDict):
    type: Literal["divider"]


class MessagePresentationButtonsBlock(TypedDict):
    type: Literal["buttons"]
    buttons: list[MessagePresentationButton]


class MessagePresentationSelectBlock(TypedDict, total=False):
    type: Literal["select"]
    placeholder: str
    options: list[MessagePresentationOption]


MessagePresentationInteractiveBlock = MessagePresentationButtonsBlock | MessagePresentationSelectBlock
MessagePresentationBlock = (
    MessagePresentationTextBlock
    | MessagePresentationContextBlock
    | MessagePresentationDividerBlock
    | MessagePresentationButtonsBlock
    | MessagePresentationSelectBlock
)


class MessagePresentation(TypedDict, total=False):
    title: str
    tone: MessagePresentationTone
    blocks: list[MessagePresentationBlock]


class ReplyPayloadDeliveryPin(TypedDict, total=False):
    enabled: bool
    notify: bool
    required: bool


class ReplyPayloadDelivery(TypedDict, total=False):
    pin: bool | ReplyPayloadDeliveryPin


_VALID_BUTTON_STYLES = frozenset({"primary", "secondary", "success", "danger"})
_VALID_TONES = frozenset({"info", "success", "warning", "danger", "neutral"})


def resolve_message_presentation_action_value(
    action: MessagePresentationAction | None,
) -> str | None:
    if action is None:
        return None
    action_type = action.get("type")
    if action_type == "command":
        return action.get("command")
    if action_type == "callback":
        return action.get("value")
    return None


def resolve_message_presentation_control_value(
    control: Mapping[str, Any] | None,
) -> str | None:
    if control is None:
        return None
    action = control.get("action")
    value = resolve_message_presentation_action_value(action) if isinstance(action, Mapping) else None
    if value is not None:
        return value
    raw_value = control.get("value")
    return raw_value if isinstance(raw_value, str) else None


InteractiveReplyButton = MessagePresentationButton
InteractiveReplyOption = MessagePresentationOption


def normalize_button_style(value: Any) -> str | None:
    style = normalize_optional_lowercase_string(value)
    if style and style in _VALID_BUTTON_STYLES:
        return style
    return None


def normalize_presentation_tone(value: Any) -> str | None:
    tone = normalize_optional_lowercase_string(value)
    if tone and tone in _VALID_TONES:
        return tone
    return None


def normalize_button_action(raw: Any) -> MessagePresentationAction | None:
    record = as_optional_record(raw)
    if record is None:
        return None
    action_type = normalize_optional_lowercase_string(record.get("type"))
    if action_type == "command":
        command = normalize_optional_string(record.get("command"))
        if command:
            return {"type": "command", "command": command}
        return None
    if action_type == "callback":
        value = normalize_optional_string(record.get("value"))
        if value:
            return {"type": "callback", "value": value}
        return None
    return None


def normalize_button_label(value: Any) -> str | None:
    return normalize_optional_string(value)


def _normalize_button_entry(raw: Any) -> MessagePresentationButton | None:
    record = as_optional_record(raw)
    if record is None:
        return None
    label = normalize_optional_string(record.get("label")) or normalize_optional_string(
        record.get("text")
    )
    value = (
        normalize_optional_string(record.get("value"))
        or normalize_optional_string(record.get("callbackData"))
        or normalize_optional_string(record.get("callback_data"))
    )
    action = normalize_button_action(record.get("action"))
    url = normalize_optional_string(record.get("url"))
    web_app_record = as_optional_record(record.get("webApp")) or as_optional_record(
        record.get("web_app")
    )
    web_app_url = normalize_optional_string(web_app_record.get("url")) if web_app_record else None
    if not label:
        return None
    button: MessagePresentationButton = {"label": label}
    if action:
        button["action"] = action
    if value:
        button["value"] = value
    if url:
        button["url"] = url
    if web_app_url is not None:
        button["webApp"] = {"url": web_app_url}
    priority = record.get("priority")
    if isinstance(priority, int) and not isinstance(priority, bool):
        button["priority"] = priority
    if record.get("disabled") is True:
        button["disabled"] = True
    if record.get("reusable") is True:
        button["reusable"] = True
    style = normalize_button_style(record.get("style"))
    if style:
        button["style"] = style
    return button


def normalize_button(raw: Any) -> MessagePresentationButton | None:
    return _normalize_button_entry(raw)


def normalize_buttons(value: Any) -> list[MessagePresentationButton]:
    return _normalize_list(value, _normalize_button_entry)


def _normalize_option(raw: Any) -> MessagePresentationOption | None:
    record = as_optional_record(raw)
    if record is None:
        return None
    label = normalize_optional_string(record.get("label")) or normalize_optional_string(
        record.get("text")
    )
    action = normalize_button_action(record.get("action"))
    value = normalize_optional_string(record.get("value"))
    if value is None:
        value = resolve_message_presentation_action_value(action) if action else None
    if not label or not value:
        return None
    option: MessagePresentationOption = {"label": label, "value": value}
    if action:
        option["action"] = action
    return option


def _normalize_list(
    value: Any, normalize_entry: Any
) -> list[Any]:
    if not isinstance(value, list):
        return []
    result: list[Any] = []
    for entry in value:
        normalized = normalize_entry(entry)
        if normalized is not None:
            result.append(normalized)
    return result


def _normalize_interactive_block(raw: Any) -> InteractiveReplyBlock | None:
    record = as_optional_record(raw)
    if record is None:
        return None
    block_type = normalize_optional_lowercase_string(record.get("type"))
    if block_type == "text":
        text = normalize_optional_string(record.get("text"))
        if text:
            return {"type": "text", "text": text}
        return None
    if block_type == "buttons":
        buttons = _normalize_list(record.get("buttons"), _normalize_button_entry)
        if buttons:
            return {"type": "buttons", "buttons": buttons}
        return None
    if block_type == "select":
        options = _normalize_list(record.get("options"), _normalize_option)
        if options:
            block: InteractiveReplySelectBlock = {
                "type": "select",
                "options": options,
            }
            placeholder = normalize_optional_string(record.get("placeholder"))
            if placeholder:
                block["placeholder"] = placeholder
            return block
        return None
    return None


def normalize_interactive_reply(raw: Any) -> InteractiveReply | None:
    record = as_optional_record(raw)
    if record is None:
        return None
    blocks = _normalize_list(record.get("blocks"), _normalize_interactive_block)
    if not blocks:
        return None
    return {"blocks": blocks}


def _normalize_presentation_block(raw: Any) -> MessagePresentationBlock | None:
    record = as_optional_record(raw)
    if record is None:
        return None
    block_type = normalize_optional_lowercase_string(record.get("type"))
    if block_type in ("text", "context"):
        text = normalize_optional_string(record.get("text"))
        if text:
            return {"type": block_type, "text": text}
        return None
    if block_type == "divider":
        return {"type": "divider"}
    if block_type == "buttons":
        buttons = _normalize_list(record.get("buttons"), _normalize_button_entry)
        if buttons:
            return {"type": "buttons", "buttons": buttons}
        return None
    if block_type == "select":
        options = _normalize_list(record.get("options"), _normalize_option)
        if options:
            block: MessagePresentationSelectBlock = {"type": "select", "options": options}
            placeholder = normalize_optional_string(record.get("placeholder"))
            if placeholder:
                block["placeholder"] = placeholder
            return block
        return None
    return None


def normalize_message_presentation(raw: Any) -> MessagePresentation | None:
    record = as_optional_record(raw)
    if record is None:
        return None
    blocks = _normalize_list(record.get("blocks"), _normalize_presentation_block)
    title = normalize_optional_string(record.get("title"))
    if not title and not blocks:
        return None
    presentation: MessagePresentation = {"blocks": blocks}
    if title:
        presentation["title"] = title
    tone = normalize_presentation_tone(record.get("tone"))
    if tone:
        presentation["tone"] = tone
    return presentation


def has_interactive_reply_blocks(value: Any) -> bool:
    return normalize_interactive_reply(value) is not None


def has_message_presentation_blocks(value: Any) -> bool:
    return normalize_message_presentation(value) is not None


def presentation_to_interactive_reply(
    presentation: Mapping[str, Any],
) -> InteractiveReply | None:
    blocks: list[InteractiveReplyBlock] = []
    title = presentation.get("title")
    if isinstance(title, str) and title:
        blocks.append({"type": "text", "text": title})
    for block in presentation.get("blocks", []) or []:
        block_type = block.get("type") if isinstance(block, Mapping) else None
        if block_type in ("text", "context"):
            text = block.get("text")
            if isinstance(text, str):
                blocks.append({"type": "text", "text": text})
            continue
        if block_type == "buttons":
            buttons_source = block.get("buttons", []) if isinstance(block, Mapping) else []
            converted: list[MessagePresentationButton] = []
            for button in buttons_source:
                if not isinstance(button, Mapping):
                    continue
                has_interactive = (
                    button.get("action")
                    or button.get("value")
                    or button.get("url")
                    or button.get("webApp")
                    or button.get("web_app")
                )
                if not has_interactive:
                    continue
                interactive_button: MessagePresentationButton = {
                    "label": button.get("label", ""),
                }
                if button.get("style") is not None:
                    interactive_button["style"] = button["style"]
                if button.get("action") is not None:
                    interactive_button["action"] = button["action"]
                if button.get("value") is not None:
                    interactive_button["value"] = button["value"]
                elif isinstance(button.get("action"), Mapping):
                    action_type = button["action"].get("type")
                    if action_type == "command":
                        command_val = button["action"].get("command")
                        if isinstance(command_val, str):
                            interactive_button["value"] = command_val
                    elif action_type == "callback":
                        callback_val = button["action"].get("value")
                        if isinstance(callback_val, str):
                            interactive_button["value"] = callback_val
                if button.get("url") is not None:
                    interactive_button["url"] = button["url"]
                web_app = button.get("webApp") or button.get("web_app")
                if web_app is not None:
                    interactive_button["webApp"] = web_app
                if button.get("priority") is not None:
                    interactive_button["priority"] = button["priority"]
                if button.get("disabled") is True:
                    interactive_button["disabled"] = True
                if button.get("reusable") is True:
                    interactive_button["reusable"] = True
                converted.append(interactive_button)
            if converted:
                blocks.append({"type": "buttons", "buttons": converted})
            continue
        if block_type == "select" and isinstance(block, Mapping):
            options_source = block.get("options", []) or []
            converted_options: list[MessagePresentationOption] = []
            for option in options_source:
                if not isinstance(option, Mapping):
                    continue
                interactive_option: MessagePresentationOption = {
                    "label": option.get("label", ""),
                    "value": resolve_message_presentation_control_value(option)
                    or option.get("value", ""),
                }
                if option.get("action") is not None:
                    interactive_option["action"] = option["action"]
                converted_options.append(interactive_option)
            select_block: InteractiveReplySelectBlock = {
                "type": "select",
                "options": converted_options,
            }
            if block.get("placeholder") is not None:
                select_block["placeholder"] = block["placeholder"]
            blocks.append(select_block)
    if not blocks:
        return None
    return {"blocks": blocks}


def is_message_presentation_interactive_block(
    block: Mapping[str, Any],
) -> bool:
    return block.get("type") in ("buttons", "select")


def presentation_to_interactive_controls_reply(
    presentation: Mapping[str, Any],
) -> InteractiveReply | None:
    interactive_blocks = [
        block
        for block in presentation.get("blocks", []) or []
        if isinstance(block, Mapping)
        and is_message_presentation_interactive_block(block)
    ]
    return presentation_to_interactive_reply({"blocks": interactive_blocks})


def interactive_reply_to_presentation(
    interactive: Mapping[str, Any],
) -> MessagePresentation | None:
    blocks: list[MessagePresentationBlock] = []
    for block in interactive.get("blocks", []) or []:
        if not isinstance(block, Mapping):
            continue
        block_type = block.get("type")
        if block_type == "text":
            text = block.get("text")
            if isinstance(text, str):
                blocks.append({"type": "text", "text": text})
        elif block_type == "buttons":
            buttons = block.get("buttons", []) or []
            blocks.append({"type": "buttons", "buttons": buttons})
        elif block_type == "select":
            select_block: MessagePresentationSelectBlock = {
                "type": "select",
                "options": block.get("options", []) or [],
            }
            if block.get("placeholder") is not None:
                select_block["placeholder"] = block["placeholder"]
            blocks.append(select_block)
    if not blocks:
        return None
    return {"blocks": blocks}


def render_message_presentation_fallback_text(
    params: Mapping[str, Any],
) -> str:
    lines: list[str] = []
    text = normalize_optional_string(params.get("text"))
    if text:
        lines.append(text)
    presentation = params.get("presentation")
    if presentation is None or not isinstance(presentation, Mapping):
        rendered = "\n\n".join(lines)
        if rendered:
            return rendered
        empty_fallback = params.get("emptyFallback")
        if isinstance(empty_fallback, str):
            normalized = normalize_optional_string(empty_fallback)
            return normalized or ""
        return ""
    title = presentation.get("title")
    if isinstance(title, str) and title:
        lines.append(title)
    for block in presentation.get("blocks", []) or []:
        if not isinstance(block, Mapping):
            continue
        block_type = block.get("type")
        if block_type in ("text", "context"):
            block_text = block.get("text")
            if isinstance(block_text, str):
                lines.append(block_text)
            continue
        if block_type == "buttons":
            labels: list[str] = []
            for button in block.get("buttons", []) or []:
                if not isinstance(button, Mapping):
                    continue
                target_url = button.get("url")
                if target_url is None:
                    web_app = button.get("webApp") or button.get("web_app")
                    if isinstance(web_app, Mapping):
                        target_url = web_app.get("url")
                label = button.get("label")
                if not isinstance(label, str) or not label:
                    continue
                if isinstance(target_url, str) and target_url:
                    labels.append(f"{label}: {target_url}")
                else:
                    labels.append(label)
            if labels:
                lines.append("\n".join(f"- {label}" for label in labels))
            continue
        if block_type == "select":
            labels = [
                option.get("label")
                for option in block.get("options", []) or []
                if isinstance(option, Mapping)
                and isinstance(option.get("label"), str)
                and option["label"]
            ]
            if labels:
                placeholder = block.get("placeholder")
                if isinstance(placeholder, str) and placeholder:
                    heading = f"{placeholder}:"
                else:
                    heading = "Options:"
                lines.append(f"{heading}\n" + "\n".join(f"- {label}" for label in labels))
    rendered = "\n\n".join(lines)
    if rendered:
        return rendered
    empty_fallback = params.get("emptyFallback")
    if isinstance(empty_fallback, str):
        normalized = normalize_optional_string(empty_fallback)
        return normalized or ""
    return ""


def has_reply_channel_data(value: Any) -> bool:
    return bool(
        value
        and isinstance(value, Mapping)
        and not isinstance(value, list)
        and len(value) > 0
    )


def has_reply_content(params: Mapping[str, Any]) -> bool:
    text = normalize_optional_string(params.get("text"))
    media_url = normalize_optional_string(params.get("mediaUrl"))
    media_urls = params.get("mediaUrls")
    has_media_urls = False
    if isinstance(media_urls, list):
        has_media_urls = any(
            normalize_optional_string(entry) is not None for entry in media_urls
        )
    return bool(
        text
        or media_url
        or has_media_urls
        or has_message_presentation_blocks(params.get("presentation"))
        or has_interactive_reply_blocks(params.get("interactive"))
        or params.get("hasChannelData")
        or params.get("extraContent")
    )


def has_reply_payload_content(
    payload: Mapping[str, Any],
    options: Mapping[str, Any] | None = None,
) -> bool:
    if options is None:
        options = {}
    raw_text = payload.get("text")
    if options.get("trimText"):
        raw_text = raw_text.strip() if isinstance(raw_text, str) else raw_text
    has_channel_data = options.get("hasChannelData")
    if has_channel_data is None:
        has_channel_data = has_reply_channel_data(payload.get("channelData"))
    return has_reply_content(
        {
            "text": raw_text,
            "mediaUrl": payload.get("mediaUrl"),
            "mediaUrls": payload.get("mediaUrls"),
            "interactive": payload.get("interactive"),
            "presentation": payload.get("presentation"),
            "hasChannelData": has_channel_data,
            "extraContent": options.get("extraContent"),
        }
    )


def resolve_interactive_text_fallback(
    params: Mapping[str, Any],
) -> str | None:
    text = normalize_optional_string(params.get("text"))
    if text:
        return text
    interactive = params.get("interactive")
    blocks = interactive.get("blocks", []) if isinstance(interactive, Mapping) else []
    parts: list[str] = []
    for block in blocks or []:
        if not isinstance(block, Mapping):
            continue
        if block.get("type") != "text":
            continue
        block_text = block.get("text")
        if isinstance(block_text, str):
            trimmed = block_text.strip()
            if trimmed:
                parts.append(trimmed)
    if parts:
        return "\n\n".join(parts)
    fallback_text = params.get("text")
    return fallback_text if isinstance(fallback_text, str) else None


__all__ = [
    "InteractiveButtonStyle",
    "InteractiveReply",
    "InteractiveReplyBlock",
    "InteractiveReplyButton",
    "InteractiveReplyOption",
    "MessagePresentation",
    "MessagePresentationAction",
    "MessagePresentationBlock",
    "MessagePresentationButton",
    "MessagePresentationContextBlock",
    "MessagePresentationDividerBlock",
    "MessagePresentationButtonsBlock",
    "MessagePresentationSelectBlock",
    "MessagePresentationInteractiveBlock",
    "MessagePresentationOption",
    "MessagePresentationTone",
    "ReplyPayloadDelivery",
    "ReplyPayloadDeliveryPin",
    "has_interactive_reply_blocks",
    "has_message_presentation_blocks",
    "has_reply_channel_data",
    "has_reply_content",
    "has_reply_payload_content",
    "interactive_reply_to_presentation",
    "is_message_presentation_interactive_block",
    "normalize_button",
    "normalize_button_action",
    "normalize_button_label",
    "normalize_button_style",
    "normalize_buttons",
    "normalize_interactive_reply",
    "normalize_message_presentation",
    "normalize_presentation_tone",
    "presentation_to_interactive_controls_reply",
    "presentation_to_interactive_reply",
    "render_message_presentation_fallback_text",
    "resolve_interactive_text_fallback",
    "resolve_message_presentation_action_value",
    "resolve_message_presentation_control_value",
]
