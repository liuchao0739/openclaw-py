from typing import Optional

from .prompt_style import PromptStyle


class PromptSelectStyledParams:
    def __init__(
        self,
        selected_style: Optional[PromptStyle] = None,
        focused_style: Optional[PromptStyle] = None,
        normal_style: Optional[PromptStyle] = None,
        max_width: int = 80,
        show_index: bool = False
    ):
        self.selected_style = selected_style or PromptStyle(fg="\x1b[32m", bold=True)
        self.focused_style = focused_style or PromptStyle(fg="\x1b[36m")
        self.normal_style = normal_style or PromptStyle()
        self.max_width = max_width
        self.show_index = show_index