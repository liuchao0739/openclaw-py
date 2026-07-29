"""Builds a JSON-RPC success response, using null for notifications or malformed missing ids.

Mirrors src/gateway/mcp-http.protocol.ts.
"""

from __future__ import annotations

from typing import Any

MCP_LOOPBACK_SERVER_NAME: Any = None
MCP_LOOPBACK_SERVER_VERSION: Any = None
MCP_LOOPBACK_SUPPORTED_PROTOCOL_VERSIONS: Any = None

JsonRpcRequest = Any

def json_rpc_result(*args: Any, **kwargs: Any) -> Any: ...
def json_rpc_error(*args: Any, **kwargs: Any) -> Any: ...
