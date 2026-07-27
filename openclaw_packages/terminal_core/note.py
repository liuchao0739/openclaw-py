from typing import Optional


def format_note(text: str, type: str = "info") -> str:
    type_lower = type.lower()
    if type_lower == "warning":
        prefix = "\x1b[33m⚠️"
    elif type_lower == "error":
        prefix = "\x1b[31m❌"
    elif type_lower == "success":
        prefix = "\x1b[32m✅"
    else:
        prefix = "\x1b[34mℹ️"

    return f"{prefix} {text}\x1b[0m"