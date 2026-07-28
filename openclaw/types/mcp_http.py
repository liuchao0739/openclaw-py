from typing import Any, Callable, Optional


class StreamableHTTPServerTransportOptions:
    session_id_generator: Optional[Callable[[], str]]


class StreamableHTTPServerTransport:
    def __init__(self, options: Optional[StreamableHTTPServerTransportOptions] = None):
        ...

    @property
    def session_id(self) -> Optional[str]:
        ...

    async def start(self) -> None:
        ...

    async def close(self) -> None:
        ...

    async def send(self, message: Any, options: Optional[dict] = None) -> None:
        ...

    async def handle_request(self, req: Any, res: Any, parsed_body: Any = None) -> None:
        ...
