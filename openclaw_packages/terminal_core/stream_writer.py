import sys
from typing import Callable, Optional


class SafeStreamWriter:
    def __init__(self, before_write: Optional[Callable[[], None]] = None, on_broken_pipe: Optional[Callable[[Exception, object], None]] = None):
        self._closed = False
        self._notified = False
        self._before_write = before_write
        self._on_broken_pipe = on_broken_pipe

    def _is_broken_pipe_error(self, err: Exception) -> bool:
        return hasattr(err, 'errno') and err.errno in (32, 5)

    def _note_broken_pipe(self, err: Exception, stream: object) -> None:
        if self._notified:
            return
        self._notified = True
        if self._on_broken_pipe:
            self._on_broken_pipe(err, stream)

    def _handle_error(self, err: Exception, stream: object) -> bool:
        if not self._is_broken_pipe_error(err):
            raise err
        self._closed = True
        self._note_broken_pipe(err, stream)
        return False

    def write(self, stream, text: str) -> bool:
        if self._closed:
            return False
        try:
            if self._before_write:
                self._before_write()
        except Exception as err:
            return self._handle_error(err, sys.stderr)
        try:
            stream.write(text)
            return not self._closed
        except Exception as err:
            return self._handle_error(err, stream)

    def write_line(self, stream, text: str) -> bool:
        return self.write(stream, f"{text}\n")

    def reset(self) -> None:
        self._closed = False
        self._notified = False

    def is_closed(self) -> bool:
        return self._closed


def create_safe_stream_writer(before_write: Optional[Callable[[], None]] = None, on_broken_pipe: Optional[Callable[[Exception, object], None]] = None) -> SafeStreamWriter:
    return SafeStreamWriter(before_write, on_broken_pipe)