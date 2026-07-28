from typing import Any, Callable, Dict, List, Optional, Union


class PtyExitEvent:
    exit_code: int
    signal: Optional[int]


PtyListener = Callable[[Any], None]


class PtyHandle:
    pid: int
    write: Callable[[Union[str, bytes]], None]
    onData: Callable[[PtyListener[str]], None]
    onExit: Callable[[PtyListener[PtyExitEvent]], None]


def PtySpawn(
    file: str,
    args: Union[List[str], str],
    options: Optional[Dict[str, Any]] = None,
) -> PtyHandle:
    ...


def spawn(
    file: str,
    args: Union[List[str], str],
    options: Optional[Dict[str, Any]] = None,
) -> PtyHandle:
    ...
