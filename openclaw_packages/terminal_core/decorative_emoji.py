EMOJI_STATUS_MAP = {
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "loading": "⏳",
    "done": "✅",
    "pending": "🔄",
}


def get_status_emoji(status: str) -> str:
    return EMOJI_STATUS_MAP.get(status.lower(), "📌")


def decorate_with_emoji(text: str, emoji: str) -> str:
    return f"{emoji} {text}"