from __future__ import annotations

import socket
import subprocess
from typing import Any


def is_port_available(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


def find_available_port(
    start: int = 18000,
    end: int = 19000,
    host: str = "127.0.0.1",
) -> int:
    for port in range(start, end + 1):
        if is_port_available(port, host):
            return port
    raise RuntimeError(f"No available port found in range {start}-{end}")


def get_process_using_port(port: int) -> int | None:
    try:
        result = subprocess.run(
            ["lsof", "-ti", f"tcp:{port}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.strip().split("\n")[0])
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
        pass
    return None


def format_port_listening_info(port: int, host: str = "127.0.0.1") -> str:
    pid = get_process_using_port(port)
    if pid:
        return f"Port {port} is in use by PID {pid}"
    return f"Port {port} is available on {host}"
