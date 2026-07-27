from typing import List, Optional

from .ansi import visible_width, truncate_to_visible_width
from .prompt_style import PromptStyle


def render_prompt_select_option(
    text: str,
    is_selected: bool,
    is_focused: bool,
    index: int,
    max_width: int,
    selected_style: PromptStyle,
    focused_style: PromptStyle,
    normal_style: PromptStyle
) -> str:
    truncated = truncate_to_visible_width(text, max_width - 4)
    padding = " " * (max_width - visible_width(truncated) - 4)

    prefix = "❯ " if is_selected else "  "

    if is_selected and is_focused:
        style = selected_style
    elif is_focused:
        style = focused_style
    else:
        style = normal_style

    return f"{style.to_ansi()}{prefix}{truncated}{padding}\x1b[0m"


def render_prompt_select(
    options: List[str],
    selected_index: int,
    focused_index: int,
    max_width: int,
    selected_style: PromptStyle,
    focused_style: PromptStyle,
    normal_style: PromptStyle
) -> str:
    lines = []
    for i, option in enumerate(options):
        is_selected = i == selected_index
        is_focused = i == focused_index
        line = render_prompt_select_option(
            option, is_selected, is_focused, i, max_width,
            selected_style, focused_style, normal_style
        )
        lines.append(line)
    return "\n".join(lines)