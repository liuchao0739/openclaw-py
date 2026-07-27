import re


def escape_for_shell(text: str) -> str:
    if not text:
        return "''"
    if re.match(r"^[a-zA-Z0-9_.-]+$", text):
        return text
    escaped = text.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


def truncate_with_ellipsis(text: str, max_length: int, ellipsis: str = "...") -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length - len(ellipsis)] + ellipsis


def indent_text(text: str, level: int = 1, indent_char: str = "  ") -> str:
    indent = indent_char * level
    lines = text.split("\n")
    return "\n".join(f"{indent}{line}" for line in lines)