"""Config root modules: mutation conflict error, talk defaults, bot loop protection."""

from .mutation_conflict import ConfigMutationConflictError
from .talk_defaults import describe_talk_silence_timeout_defaults
from .bot_loop_protection import ChannelBotLoopProtectionConfig

__all__ = [
    "ConfigMutationConflictError",
    "describe_talk_silence_timeout_defaults",
    "ChannelBotLoopProtectionConfig",
]
