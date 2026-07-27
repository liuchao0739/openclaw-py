from typing import List


TERMINAL_COLORS = [
    "\x1b[30m",
    "\x1b[31m",
    "\x1b[32m",
    "\x1b[33m",
    "\x1b[34m",
    "\x1b[35m",
    "\x1b[36m",
    "\x1b[37m",
    "\x1b[90m",
    "\x1b[91m",
    "\x1b[92m",
    "\x1b[93m",
    "\x1b[94m",
    "\x1b[95m",
    "\x1b[96m",
    "\x1b[97m",
]


def get_color(index: int) -> str:
    return TERMINAL_COLORS[index % len(TERMINAL_COLORS)]


def rainbow_text(text: str) -> str:
    result = []
    for i, char in enumerate(text):
        result.append(f"{get_color(i)}{char}")
    result.append("\x1b[0m")
    return "".join(result)