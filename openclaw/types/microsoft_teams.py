from typing import Any, Callable, Dict, Optional


class App:
    def __init__(self, client_id: str, client_secret: str, tenant_id: Optional[str] = None):
        ...

    async def getBotToken(self) -> Optional[Any]:
        ...

    async def getAppGraphToken(self) -> Optional[Any]:
        ...


class _Conversations:
    def __init__(self, service_url: str):
        ...

    def activities(self, conversation_id: str) -> "_Activities":
        ...


class _Activities:
    async def create(self, activity: Dict[str, Any]) -> Any:
        ...


class Client:
    def __init__(
        self,
        service_url: str,
        options: Optional[Dict[str, Any]] = None,
    ):
        ...

    @property
    def conversations(self) -> _Conversations:
        ...
