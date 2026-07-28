from typing import Callable, Optional


class PreviewThemeOptions:
    sanitize: Optional[Callable[[str], str]]


def applyPreviewTheme(html: str, options: Optional[PreviewThemeOptions] = None) -> str:
    ...
