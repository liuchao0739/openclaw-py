from __future__ import annotations

import textwrap
from typing import Any


def format_help_text(text: str, columns: int = 80) -> str:
    if not text:
        return ""
    return textwrap.fill(text, width=columns)


def format_help_section(title: str, items: list[tuple[str, str]], columns: int = 80) -> str:
    lines = [title, ""]
    for name, description in items:
        if description:
            wrapped = textwrap.fill(
                description, width=columns - 24, initial_indent="  ", subsequent_indent="    "
            )
            lines.append(f"  {name:<20}  {wrapped}")
        else:
            lines.append(f"  {name}")
    return "\n".join(lines)


def indent_text(text: str, spaces: int = 2) -> str:
    if not text:
        return ""
    prefix = " " * spaces
    return "\n".join(f"{prefix}{line}" for line in text.split("\n"))
