from __future__ import annotations

from openclaw.cli.argv import (
    get_command_path_with_root_options,
    get_primary_command,
    is_help_or_version_invocation,
    is_root_help_invocation,
)


def resolve_cli_argv_invocation(argv: list[str]) -> dict:
    return {
        "argv": argv,
        "commandPath": get_command_path_with_root_options(argv, 2),
        "primary": get_primary_command(argv),
        "hasHelpOrVersion": is_help_or_version_invocation(argv),
        "isRootHelpInvocation": is_root_help_invocation(argv),
    }
