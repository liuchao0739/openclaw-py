"""Command analysis package — policy and segment analysis."""

from .policy import (
    analyze_command_for_policy,
    detect_policy_inline_eval,
    detect_inline_eval_in_segments,
    ExecCommandSegment,
    ExecCommandAnalysis,
)

__all__ = [
    "analyze_command_for_policy",
    "detect_policy_inline_eval",
    "detect_inline_eval_in_segments",
    "ExecCommandSegment",
    "ExecCommandAnalysis",
]
