"""Gateway service status command entrypoint."""

from __future__ import annotations

from typing import Any

from openclaw.cli.daemon_cli.types import DaemonStatusOptions


async def run_daemon_status(opts: dict[str, Any]) -> dict[str, Any]:
    """Run Gateway status diagnostics and apply --require-rpc exit behavior.

    Returns a status dict with 'ok', 'output', and 'exitCode' fields.
    """
    require_rpc = opts.get("requireRpc", False)
    probe = opts.get("probe", True)
    json_output = opts.get("json", False)
    deep = opts.get("deep", False)

    if require_rpc and not probe:
        return {
            "ok": False,
            "output": "Gateway status failed: --require-rpc needs probing enabled.",
            "exitCode": 1,
        }

    # Gather status (deferred to daemon/inspect module)
    status: dict[str, Any] = {"installed": False, "running": False, "rpc": {"ok": False}}

    try:
        from openclaw.daemon.inspect import gather_daemon_status

        status = await gather_daemon_status({
            "rpc": opts.get("rpc", {}),
            "probe": probe,
            "requireRpc": require_rpc,
            "deep": deep,
        })
    except Exception:
        pass

    # Print status
    if json_output:
        import json

        output = json.dumps(status, indent=2)
    else:
        lines: list[str] = []
        lines.append(f"Installed: {'yes' if status.get('installed') else 'no'}")
        lines.append(f"Running: {'yes' if status.get('running') else 'no'}")
        rpc = status.get("rpc", {})
        if isinstance(rpc, dict):
            lines.append(f"RPC: {'ok' if rpc.get('ok') else 'unreachable'}")
        output = "\n".join(lines)

    exit_code = 0
    if require_rpc:
        rpc = status.get("rpc", {})
        if isinstance(rpc, dict) and not rpc.get("ok"):
            exit_code = 1

    return {"ok": exit_code == 0, "output": output, "exitCode": exit_code, "status": status}
