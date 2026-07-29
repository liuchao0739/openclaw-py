import asyncio
from typing import Optional

_active_turns: dict = {}
_active_turns_lock = asyncio.Lock()


async def track_codex_conversation_active_turn(params: dict):
    key = params["sessionFile"]
    turn_id = params["turnId"]
    async with _active_turns_lock:
        _active_turns[key] = turn_id

    def _cleanup():
        async def _remove():
            async with _active_turns_lock:
                if _active_turns.get(key) == turn_id:
                    _active_turns.pop(key, None)
        asyncio.ensure_future(_remove())

    return _cleanup


async def get_codex_conversation_active_turn(session_file: str) -> Optional[str]:
    async with _active_turns_lock:
        return _active_turns.get(session_file)


async def clear_codex_conversation_active_turn(session_file: str) -> None:
    async with _active_turns_lock:
        _active_turns.pop(session_file, None)
