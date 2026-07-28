CLAUDE_CLI_BACKEND_ID = "claude-cli"

CLAUDE_CLI_DEFAULT_MODEL_REF = f"{CLAUDE_CLI_BACKEND_ID}/claude-opus-4-8"

CLAUDE_CLI_DEFAULT_ALLOWLIST_REFS = [
    CLAUDE_CLI_DEFAULT_MODEL_REF,
    f"{CLAUDE_CLI_BACKEND_ID}/claude-opus-4-7",
    f"{CLAUDE_CLI_BACKEND_ID}/claude-sonnet-4-6",
    f"{CLAUDE_CLI_BACKEND_ID}/claude-opus-4-6",
]

CLAUDE_CLI_MODEL_ALIASES: dict[str, str] = {
    "opus": "opus",
    "opus-4.8": "claude-opus-4-8",
    "opus-4.7": "claude-opus-4-7",
    "opus-4.6": "claude-opus-4-6",
    "claude-opus-4-8": "claude-opus-4-8",
    "claude-opus-4-7": "claude-opus-4-7",
    "claude-opus-4-6": "claude-opus-4-6",
    "sonnet": "sonnet",
    "sonnet-4.6": "claude-sonnet-4-6",
    "claude-sonnet-4-6": "claude-sonnet-4-6",
    "haiku": "haiku",
}

CLAUDE_CLI_SESSION_ID_FIELDS = [
    "session_id",
    "sessionId",
    "conversation_id",
    "conversationId",
]