from typing import Optional


def ellipsis(text: str, max_length: int, middle: bool = False) -> str:
    if len(text) <= max_length:
        return text

    if middle:
        half = (max_length - 3) // 2
        return text[:half] + "..." + text[-half:]
    return text[:max_length - 3] + "..."


def truncate(text: str, max_length: int) -> str:
    return text[:max_length]


def pad(text: str, length: int, align: str = "left") -> str:
    if len(text) >= length:
        return text

    if align == "right":
        return text.rjust(length)
    elif align == "center":
        return text.center(length)
    return text.ljust(length)


def repeat_char(char: str, count: int) -> str:
    return char * count


def surround(text: str, prefix: str, suffix: str) -> str:
    return f"{prefix}{text}{suffix}"