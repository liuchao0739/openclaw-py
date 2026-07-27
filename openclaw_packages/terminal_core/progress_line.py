from typing import Optional

from .ansi import visible_width


def render_progress_line(
    current: int,
    total: int,
    width: int = 40,
    filled_char: str = "█",
    empty_char: str = "░",
    prefix: str = "",
    suffix: str = ""
) -> str:
    if total <= 0:
        percentage = 0
    else:
        percentage = min(100, max(0, (current / total) * 100))

    filled = int((percentage / 100) * width)
    empty = width - filled

    bar = filled_char * filled + empty_char * empty

    prefix_len = visible_width(prefix) if prefix else 0
    suffix_len = visible_width(suffix) if suffix else 0

    result = f"{prefix}{bar}{suffix}" if prefix or suffix else bar
    return result


def render_progress_text(current: int, total: int) -> str:
    if total <= 0:
        return f"{current}"
    percentage = int((current / total) * 100)
    return f"{current}/{total} ({percentage}%)"