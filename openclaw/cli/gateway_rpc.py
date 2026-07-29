from __future__ import annotations

from typing import Any

from openclaw.cli.gateway_rpc_types import GatewayRpcOpts


def build_gateway_rpc_call(opts: GatewayRpcOpts) -> dict:
    return dict(opts)


def parse_gateway_rpc_response(response: Any) -> dict:
    if isinstance(response, dict):
        return response
    return {"result": response}
