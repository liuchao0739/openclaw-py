from typing import Optional


def format_health_status(status: str, value: Optional[str] = None) -> str:
    status_lower = status.lower()
    if status_lower == "healthy":
        color = "\x1b[32m"
        icon = "✓"
    elif status_lower == "degraded":
        color = "\x1b[33m"
        icon = "~"
    elif status_lower == "unhealthy":
        color = "\x1b[31m"
        icon = "✗"
    else:
        color = "\x1b[37m"
        icon = "?"

    if value:
        return f"{color}{icon} {status} ({value})\x1b[0m"
    return f"{color}{icon} {status}\x1b[0m"