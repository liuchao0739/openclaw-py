"""Gateway server package — re-exports the FastAPI app from _server_app."""

from ._server_app import create_app, app, HealthResponse

__all__ = ["create_app", "app", "HealthResponse"]
