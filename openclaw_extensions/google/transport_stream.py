import json
import time
from typing import Optional, Dict, Any, List, Callable, AsyncIterator


class StreamEvent:
    def __init__(
        self,
        event_type: str,
        data: Dict[str, Any],
        raw_data: str = "",
        timestamp: Optional[float] = None,
    ):
        self.event_type = event_type
        self.data = data
        self.raw_data = raw_data
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "data": self.data,
            "raw_data": self.raw_data,
            "timestamp": self.timestamp,
        }


class TransportStream:
    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
        on_event: Optional[Callable[[StreamEvent], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        on_close: Optional[Callable[[], None]] = None,
    ):
        self.url = url
        self.headers = headers or {}
        self.params = params or {}
        self._on_event = on_event
        self._on_error = on_error
        self._on_close = on_close
        self._events: List[StreamEvent] = []
        self._closed = False

    @property
    def is_closed(self) -> bool:
        return self._closed

    async def send(self, data: Dict[str, Any]) -> None:
        pass

    async def receive(self) -> Optional[StreamEvent]:
        if self._events:
            return self._events.pop(0)
        return None

    def add_event(self, event: StreamEvent) -> None:
        self._events.append(event)
        if self._on_event:
            self._on_event(event)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._on_close:
            self._on_close()

    def get_events(self) -> List[StreamEvent]:
        return list(self._events)

    def clear_events(self) -> None:
        self._events.clear()

    async def stream(self, data_iterator: AsyncIterator[Dict[str, Any]]) -> AsyncIterator[StreamEvent]:
        async for data in data_iterator:
            event = StreamEvent(
                event_type="data",
                data=data,
            )
            self.add_event(event)
            yield event
        self.close()


class SSEParser:
    def __init__(self):
        self._buffer = ""
        self._events: List[StreamEvent] = []

    def feed(self, data: str) -> List[StreamEvent]:
        self._buffer += data
        parsed_events = []

        while "\n\n" in self._buffer:
            event_block, self._buffer = self._buffer.split("\n\n", 1)
            event = self._parse_event_block(event_block)
            if event:
                parsed_events.append(event)
                self._events.append(event)

        return parsed_events

    def _parse_event_block(self, block: str) -> Optional[StreamEvent]:
        event_type = "message"
        data_lines = []

        for line in block.split("\n"):
            line = line.strip()
            if line.startswith("event:"):
                event_type = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].strip())

        data_str = "\n".join(data_lines)
        try:
            parsed_data = json.loads(data_str)
        except (ValueError, json.JSONDecodeError):
            parsed_data = {"raw": data_str}

        return StreamEvent(
            event_type=event_type,
            data=parsed_data,
            raw_data=data_str,
        )

    def get_events(self) -> List[StreamEvent]:
        return list(self._events)

    def reset(self) -> None:
        self._buffer = ""
        self._events.clear()


class GoogleTransportStream:
    def __init__(
        self,
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
    ):
        self.base_url = base_url
        self.headers = headers or {}
        self.params = params or {}
        self._parser = SSEParser()

    def parse_stream_response(self, response_text: str) -> List[StreamEvent]:
        return self._parser.feed(response_text)

    def build_url(self, path: str) -> str:
        url = f"{self.base_url}{path}"
        if self.params:
            query_string = "&".join(f"{k}={v}" for k, v in self.params.items())
            url = f"{url}?{query_string}"
        return url

    def get_parser(self) -> SSEParser:
        return self._parser