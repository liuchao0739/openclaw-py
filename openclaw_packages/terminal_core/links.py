import re

LINK_PATTERN = re.compile(
    r"(https?://[^\s<>\"']+|www\.[^\s<>\"']+)",
    re.IGNORECASE
)


def find_links(text: str) -> list[str]:
    return LINK_PATTERN.findall(text)


def format_link(url: str, text: Optional[str] = None) -> str:
    if text is None:
        text = url
    return f"\x1b]8;;{url}\x1b\\{text}\x1b]8;;\x1b\\"


def has_links(text: str) -> bool:
    return LINK_PATTERN.search(text) is not None