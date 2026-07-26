"""Agent harness prompt and compaction hook helpers.

Harness runtimes use this to run plugin hooks around prompt construction and
compaction while keeping hook failures non-fatal.
"""

from __future__ import annotations

from typing import Any

from openclaw.agents.harness.hook_context import build_agent_hook_context


def _get_global_hook_runner() -> Any | None:
    try:
        from openclaw.plugins.hook_runner_global import get_global_hook_runner
    except Exception:
        return None
    return get_global_hook_runner()


def _join_present_text_segments(segments: list[Any]) -> str | None:
    parts = [s for s in segments if isinstance(s, str) and s.strip()]
    return "\n".join(parts) if parts else None


def _wrap_plugin_system_context_section(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value


async def resolve_agent_harness_before_prompt_build_result(
    params: dict[str, Any],
) -> dict[str, str]:
    """Run before-prompt hooks and return the adjusted prompt fields."""
    hook_runner = _get_global_hook_runner()
    if hook_runner is None or (
        not hook_runner.has_hooks("before_prompt_build")
        and not hook_runner.has_hooks("before_agent_start")
    ):
        return {
            "prompt": params["prompt"],
            "developerInstructions": params["developerInstructions"],
        }

    hook_ctx = build_agent_hook_context(params["ctx"])
    prompt_event = {"prompt": params["prompt"], "messages": params.get("messages", [])}

    prompt_build_result = None
    if hook_runner.has_hooks("before_prompt_build"):
        try:
            prompt_build_result = await hook_runner.run_before_prompt_build(prompt_event, hook_ctx)
        except Exception:
            prompt_build_result = None

    before_agent_start_result = None
    if hook_runner.has_hooks("before_agent_start"):
        try:
            before_agent_start_result = await hook_runner.run_before_agent_start(
                prompt_event, hook_ctx
            )
        except Exception:
            before_agent_start_result = None

    system_prompt = _resolve_prompt_build_system_prompt(
        params["developerInstructions"], prompt_build_result, before_agent_start_result
    )

    prepend_context = _join_present_text_segments(
        [
            prompt_build_result.get("prependContext") if prompt_build_result else None,
            before_agent_start_result.get("prependContext") if before_agent_start_result else None,
        ]
    )

    developer_instructions = _join_present_text_segments(
        [
            _wrap_plugin_system_context_section(
                prompt_build_result.get("prependSystemContext") if prompt_build_result else None
            ),
            _wrap_plugin_system_context_section(
                before_agent_start_result.get("prependSystemContext")
                if before_agent_start_result
                else None
            ),
            system_prompt,
            _wrap_plugin_system_context_section(
                prompt_build_result.get("appendSystemContext") if prompt_build_result else None
            ),
            _wrap_plugin_system_context_section(
                before_agent_start_result.get("appendSystemContext")
                if before_agent_start_result
                else None
            ),
        ]
    )

    return {
        "prompt": prepend_context if prepend_context else params["prompt"],
        "developerInstructions": developer_instructions
        if developer_instructions
        else system_prompt,
    }


def _resolve_prompt_build_system_prompt(
    developer_instructions: str,
    prompt_build_result: dict[str, Any] | None,
    before_agent_start_result: dict[str, Any] | None,
) -> str:
    if prompt_build_result and isinstance(prompt_build_result.get("systemPrompt"), str):
        return prompt_build_result["systemPrompt"]
    if before_agent_start_result and isinstance(before_agent_start_result.get("systemPrompt"), str):
        return before_agent_start_result["systemPrompt"]
    return developer_instructions


async def run_agent_harness_before_compaction_hook(params: dict[str, Any]) -> None:
    """Run best-effort before-compaction hooks for a harness session."""
    hook_runner = _get_global_hook_runner()
    if hook_runner is None or not hook_runner.has_hooks("before_compaction"):
        return
    try:
        messages = params.get("messages")
        await hook_runner.run_before_compaction(
            {
                "messageCount": len(messages) if messages is not None else -1,
                **({"messages": messages} if messages is not None else {}),
                "sessionFile": params["sessionFile"],
            },
            build_agent_hook_context(params["ctx"]),
        )
    except Exception:
        pass


async def run_agent_harness_after_compaction_hook(params: dict[str, Any]) -> None:
    """Run best-effort after-compaction hooks for a harness session."""
    hook_runner = _get_global_hook_runner()
    if hook_runner is None or not hook_runner.has_hooks("after_compaction"):
        return
    try:
        messages = params.get("messages")
        await hook_runner.run_after_compaction(
            {
                "messageCount": len(messages) if messages is not None else -1,
                "compactedCount": params.get("compactedCount", 0),
                "sessionFile": params["sessionFile"],
            },
            build_agent_hook_context(params["ctx"]),
        )
    except Exception:
        pass
