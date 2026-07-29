from __future__ import annotations

from openclaw.cli.ports import parse_tcp_port


def resolve_gateway_port(raw: object) -> int | None:
    return parse_tcp_port(raw)


def get_gateway_port_flag_value(argv: list[str]) -> int | None:
    args = argv[2:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--port":
            next_val = args[i + 1] if i + 1 < len(args) else None
            if next_val:
                return parse_tcp_port(next_val)
            return None
        if arg.startswith("--port="):
            return parse_tcp_port(arg[len("--port=") :])
        i += 1
    return None
