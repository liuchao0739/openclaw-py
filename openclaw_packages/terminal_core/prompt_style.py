from typing import Dict, Optional


class PromptStyle:
    def __init__(self, fg: Optional[str] = None, bg: Optional[str] = None, bold: bool = False, dim: bool = False):
        self.fg = fg
        self.bg = bg
        self.bold = bold
        self.dim = dim

    def to_ansi(self) -> str:
        codes = []
        if self.fg:
            codes.append(self.fg)
        if self.bg:
            codes.append(self.bg)
        if self.bold:
            codes.append("\x1b[1m")
        if self.dim:
            codes.append("\x1b[2m")
        return "".join(codes)


def parse_prompt_style(data: Dict[str, bool]) -> PromptStyle:
    fg_map = {
        "fgBlack": "\x1b[30m",
        "fgRed": "\x1b[31m",
        "fgGreen": "\x1b[32m",
        "fgYellow": "\x1b[33m",
        "fgBlue": "\x1b[34m",
        "fgMagenta": "\x1b[35m",
        "fgCyan": "\x1b[36m",
        "fgWhite": "\x1b[37m",
    }
    bg_map = {
        "bgBlack": "\x1b[40m",
        "bgRed": "\x1b[41m",
        "bgGreen": "\x1b[42m",
        "bgYellow": "\x1b[43m",
        "bgBlue": "\x1b[44m",
        "bgMagenta": "\x1b[45m",
        "bgCyan": "\x1b[46m",
        "bgWhite": "\x1b[47m",
    }

    fg = None
    bg = None
    bold = False
    dim = False

    for key, value in data.items():
        if value and key in fg_map:
            fg = fg_map[key]
        elif value and key in bg_map:
            bg = bg_map[key]
        elif key == "bold" and value:
            bold = True
        elif key == "dim" and value:
            dim = True

    return PromptStyle(fg, bg, bold, dim)