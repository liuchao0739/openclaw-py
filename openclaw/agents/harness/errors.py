"""Agent harness error helpers.

Mirrors src/agents/harness/errors.ts.
"""

from __future__ import annotations


class MissingAgentHarnessError(Exception):
    """Error thrown when a requested harness id is not registered."""

    harness_id: str

    def __init__(self, harness_id: str) -> None:
        super().__init__(f'Requested agent harness "{harness_id}" is not registered.')
        self.harness_id = harness_id


def is_missing_agent_harness_error(err: object) -> bool:
    """Return whether an error is a missing harness error."""
    return isinstance(err, MissingAgentHarnessError)
