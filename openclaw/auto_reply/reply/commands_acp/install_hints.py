"""ACP installation hints for command replies."""

from __future__ import annotations

from typing import Any


def format_acp_install_hints(provider: str | None = None) -> str:
    """Format installation hints for ACP providers."""
    hints: list[str] = [
        "ACP (Agent Communication Protocol) setup:",
        "",
        "1. Install an ACP-compatible runtime (e.g., Claude CLI, Gemini CLI)",
        "2. Configure the provider in your openclaw.json:",
        '   {"agents": {"defaults": {"runtime": {"id": "claude"}}}}',
        "3. Ensure API keys are set in environment variables",
    ]

    if provider:
        provider_hints = _get_provider_install_hint(provider)
        if provider_hints:
            hints.append("")
            hints.append(f"Provider-specific ({provider}):")
            hints.extend(provider_hints)

    return "\n".join(hints)


def _get_provider_install_hint(provider: str) -> list[str]:
    """Get provider-specific installation hints."""
    hints: dict[str, list[str]] = {
        "claude": [
            "- Install: npm install -g @anthropic-ai/claude-cli",
            "- Set ANTHROPIC_API_KEY environment variable",
        ],
        "gemini": [
            "- Install: npm install -g @anthropic-ai/gemini-cli",
            "- Set GOOGLE_API_KEY environment variable",
        ],
        "codex": [
            "- Install: npm install -g @openai/codex",
            "- Set OPENAI_API_KEY environment variable",
        ],
    }
    return hints.get(provider.lower(), [])


def check_acp_runtime_available(provider: str | None = None) -> bool:
    """Check if an ACP runtime is available for the given provider."""
    import shutil

    runtimes: dict[str, list[str]] = {
        "claude": ["claude"],
        "gemini": ["gemini"],
        "codex": ["codex"],
    }

    if provider:
        commands = runtimes.get(provider.lower(), [])
        return any(shutil.which(cmd) is not None for cmd in commands)

    for commands in runtimes.values():
        if any(shutil.which(cmd) is not None for cmd in commands):
            return True
    return False
