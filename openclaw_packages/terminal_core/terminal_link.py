import sys

from .links import format_link


def terminal_link(text: str, url: str) -> str:
    return format_link(url, text)


def supports_hyperlinks() -> bool:
    term = sys.environ.get("TERM", "")
    if term in ("xterm-256color", "xterm-kitty", "tmux"):
        return True
    if sys.platform == "darwin":
        return True
    return False