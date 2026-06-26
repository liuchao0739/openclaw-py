"""Tests for process modules."""

from openclaw.process.lanes import CommandLane
from openclaw.process.command_queue_types import CommandQueueEnqueueOptions


class TestCommandLane:
    def test_values(self):
        assert CommandLane.Main.value == "main"
        assert CommandLane.Cron.value == "cron"
        assert CommandLane.CronNested.value == "cron-nested"
        assert CommandLane.Subagent.value == "subagent"
        assert CommandLane.Nested.value == "nested"

    def test_string_enum(self):
        assert CommandLane.Main == "main"
        assert str(CommandLane.Cron) == "CommandLane.Cron"


class TestCommandQueueEnqueueOptions:
    def test_empty(self):
        opts: CommandQueueEnqueueOptions = {}
        assert opts == {}

    def test_with_fields(self):
        opts: CommandQueueEnqueueOptions = {
            "warnAfterMs": 5000,
            "priority": "foreground",
            "taskTimeoutMs": 30000,
        }
        assert opts["warnAfterMs"] == 5000
        assert opts["priority"] == "foreground"
