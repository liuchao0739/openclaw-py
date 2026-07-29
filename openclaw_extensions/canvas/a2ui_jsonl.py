import json
from typing import List, TypedDict, Literal

A2UI_ACTION_KEYS: List[str] = [
    "beginRendering",
    "surfaceUpdate",
    "dataModelUpdate",
    "deleteSurface",
    "createSurface",
]

A2UIVersion = Literal["v0.8", "v0.9"]


class A2UIValidationResult(TypedDict):
    version: A2UIVersion
    messageCount: int


def build_a2ui_text_jsonl(text: str) -> str:
    surface_id = "main"
    root_id = "root"
    text_id = "text"
    payloads = [
        {
            "surfaceUpdate": {
                "surfaceId": surface_id,
                "components": [
                    {
                        "id": root_id,
                        "component": {
                            "Column": {"children": {"explicitList": [text_id]}}
                        },
                    },
                    {
                        "id": text_id,
                        "component": {
                            "Text": {
                                "text": {"literalString": text},
                                "usageHint": "body",
                            }
                        },
                    },
                ],
            },
        },
        {"beginRendering": {"surfaceId": surface_id, "root": root_id}},
    ]
    return "\n".join(json.dumps(payload) for payload in payloads)


def validate_a2ui_jsonl(jsonl: str) -> A2UIValidationResult:
    lines = jsonl.splitlines()
    errors: List[str] = []
    saw_v08 = False
    saw_v09 = False
    message_count = 0

    for idx, line in enumerate(lines):
        trimmed = line.strip()
        if not trimmed:
            continue
        message_count += 1
        try:
            obj = json.loads(trimmed)
        except Exception as err:
            errors.append(f"line {idx + 1}: {err}")
            continue

        if not isinstance(obj, dict) or isinstance(obj, list):
            errors.append(f"line {idx + 1}: expected JSON object")
            continue

        action_keys = [key for key in A2UI_ACTION_KEYS if key in obj]
        if len(action_keys) != 1:
            errors.append(
                f"line {idx + 1}: expected exactly one action key ({', '.join(A2UI_ACTION_KEYS)})"
            )
            continue

        if action_keys[0] == "createSurface":
            saw_v09 = True
        else:
            saw_v08 = True

    if message_count == 0:
        errors.append("no JSONL messages found")
    if saw_v08 and saw_v09:
        errors.append("mixed A2UI v0.8 and v0.9 messages in one file")

    if errors:
        raise ValueError("Invalid A2UI JSONL:\n- " + "\n- ".join(errors))

    version: A2UIVersion = "v0.9" if saw_v09 else "v0.8"
    return {"version": version, "messageCount": message_count}
