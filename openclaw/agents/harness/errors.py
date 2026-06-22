"""Agent harness error helpers."""


class MissingAgentHarnessError(Exception):
    """Raised when a requested harness id is not registered."""

    def __init__(self, harness_id: str) -> None:
        self.harness_id = harness_id
        super().__init__(f'Requested agent harness "{harness_id}" is not registered.')
        self.name = "MissingAgentHarnessError"


def is_missing_agent_harness_error(err: BaseException) -> bool:
    return isinstance(err, MissingAgentHarnessError)