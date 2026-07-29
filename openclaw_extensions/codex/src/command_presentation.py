def build_codex_command_picker_presentation(title: str, prompt: str, buttons: list) -> dict:
    return {
        "title": title,
        "blocks": [
            {"type": "text", "text": prompt},
            {
                "type": "buttons",
                "buttons": [
                    {"label": button["label"], "action": {"type": "command", "command": button["command"]}}
                    for button in buttons
                ],
            },
        ],
    }
