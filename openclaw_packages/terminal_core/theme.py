from typing import Dict, Optional


class TerminalTheme:
    def __init__(self, colors: Optional[Dict[str, str]] = None):
        self.colors = colors or {}

    def get(self, key: str, default: str = "") -> str:
        return self.colors.get(key, default)


DEFAULT_THEME = TerminalTheme({
    "primary": "\x1b[36m",
    "success": "\x1b[32m",
    "warning": "\x1b[33m",
    "error": "\x1b[31m",
    "info": "\x1b[34m",
    "bold": "\x1b[1m",
    "reset": "\x1b[0m",
})


def apply_theme(text: str, style: str, theme: TerminalTheme = DEFAULT_THEME) -> str:
    color = theme.get(style)
    if color:
        return f"{color}{text}{theme.get('reset', '\x1b[0m')}"
    return text


def theme_color(key: str, theme: TerminalTheme = DEFAULT_THEME) -> str:
    return theme.get(key, "")