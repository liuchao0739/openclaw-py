from typing import Any, Callable, Optional


class EdgeTTSOptions:
    voice: Optional[str]
    lang: Optional[str]
    output_format: Optional[str]
    save_subtitles: Optional[bool]
    proxy: Optional[str]
    rate: Optional[str]
    pitch: Optional[str]
    volume: Optional[str]
    timeout: Optional[int]


class EdgeTTS:
    def __init__(self, options: Optional[EdgeTTSOptions] = None):
        ...

    async def ttsPromise(self, text: str, output_path: str) -> None:
        ...


CHROMIUM_FULL_VERSION: str
TRUSTED_CLIENT_TOKEN: str


def generateSecMsGecToken() -> str:
    ...
