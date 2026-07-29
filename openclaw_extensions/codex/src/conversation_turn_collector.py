import asyncio
from typing import Optional


def create_codex_conversation_turn_collector(thread_id: str):
    return CodexConversationTurnCollector(thread_id)


class CodexConversationTurnCollector:
    def __init__(self, thread_id: str):
        self._thread_id = thread_id
        self._turn_id: Optional[str] = None
        self._reply_text = ""
        self._completed = asyncio.Event()

    def set_turn_id(self, turn_id: str) -> None:
        self._turn_id = turn_id

    def handle_notification(self, notification: dict) -> None:
        method = notification.get("method")
        if method == "turn/completed":
            self._reply_text = notification.get("params", {}).get("replyText", "")
            self._completed.set()

    async def wait(self, timeout_ms: Optional[int] = None) -> dict:
        if timeout_ms is not None:
            try:
                await asyncio.wait_for(self._completed.wait(), timeout=timeout_ms / 1000)
            except asyncio.TimeoutError:
                pass
        else:
            await self._completed.wait()
        return {"replyText": self._reply_text}
