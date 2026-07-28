from __future__ import annotations

from typing import Any

from openclaw.plugin_sdk.provider_auth import read_claude_cli_credentials_cached


def read_claude_cli_credentials_for_setup() -> Any:
    return read_claude_cli_credentials_cached()


def read_claude_cli_credentials_for_setup_non_interactive() -> Any:
    return read_claude_cli_credentials_cached(allowKeychainPrompt=False)


def read_claude_cli_credentials_for_runtime() -> Any:
    return read_claude_cli_credentials_cached(allowKeychainPrompt=False)