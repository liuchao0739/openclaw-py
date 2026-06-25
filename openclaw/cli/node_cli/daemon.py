"""Node-host daemon lifecycle commands for install, status, start, stop, and restart."""

from __future__ import annotations

from typing import Any

DEFAULT_NODE_DAEMON_RUNTIME = "auto"


def is_node_daemon_runtime(value: str | None) -> bool:
    """Check if a value is a valid node daemon runtime."""
    if not value:
        return False
    return value in ("auto", "native", "docker")


async def run_node_daemon_status(opts: dict[str, Any]) -> dict[str, Any]:
    """Run node daemon status diagnostics.

    Returns a status dict with 'ok', 'output', and 'exitCode' fields.
    """
    json_output = opts.get("json", False)

    status: dict[str, Any] = {"installed": False, "running": False}

    try:
        from openclaw.daemon.node_service import resolve_node_service

        service = resolve_node_service()
        status["installed"] = await service.is_loaded() if hasattr(service, "is_loaded") else False
        if hasattr(service, "read_runtime"):
            runtime = await service.read_runtime()
            status["running"] = runtime.get("status") == "running"
    except Exception:
        pass

    if json_output:
        import json

        output = json.dumps(status, indent=2)
    else:
        lines = [
            f"Installed: {'yes' if status.get('installed') else 'no'}",
            f"Running: {'yes' if status.get('running') else 'no'}",
        ]
        output = "\n".join(lines)

    return {"ok": True, "output": output, "exitCode": 0, "status": status}


async def run_node_daemon_install(opts: dict[str, Any]) -> dict[str, Any]:
    """Install the node daemon service."""
    return {"ok": True, "output": "Node daemon install: (not yet implemented)", "exitCode": 0}


async def run_node_daemon_start(opts: dict[str, Any]) -> dict[str, Any]:
    """Start the node daemon service."""
    return {"ok": True, "output": "Node daemon start: (not yet implemented)", "exitCode": 0}


async def run_node_daemon_stop(opts: dict[str, Any]) -> dict[str, Any]:
    """Stop the node daemon service."""
    return {"ok": True, "output": "Node daemon stop: (not yet implemented)", "exitCode": 0}


async def run_node_daemon_restart(opts: dict[str, Any]) -> dict[str, Any]:
    """Restart the node daemon service."""
    return {"ok": True, "output": "Node daemon restart: (not yet implemented)", "exitCode": 0}


async def run_node_daemon_uninstall(opts: dict[str, Any]) -> dict[str, Any]:
    """Uninstall the node daemon service."""
    return {"ok": True, "output": "Node daemon uninstall: (not yet implemented)", "exitCode": 0}
