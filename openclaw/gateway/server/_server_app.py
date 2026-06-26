"""FastAPI gateway HTTP server."""

from __future__ import annotations

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from openclaw import __version__
from openclaw.protocol.schema import ChatMessage, ChatRequest, ChatResponse


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = __version__


def create_app() -> FastAPI:
    app = FastAPI(title="OpenClaw Gateway (Python)", version=__version__)

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse()

    @app.post("/v1/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest) -> ChatResponse:
        last = request.messages[-1] if request.messages else ChatMessage(role="user", content="")
        reply = ChatMessage(role="assistant", content=f"echo: {last.content}")
        return ChatResponse(message=reply, session_id=request.session_id)

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            while True:
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
                else:
                    await websocket.send_text(f"ack:{data}")
        except WebSocketDisconnect:
            pass

    return app


app = create_app()
