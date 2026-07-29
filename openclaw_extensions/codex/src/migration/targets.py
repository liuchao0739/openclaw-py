import os

from openclaw.plugin_sdk.agent_runtime import (
    resolve_agent_config,
    resolve_agent_workspace_dir,
    resolve_default_agent_id,
)

from .helpers import resolve_home_path


def resolve_codex_migration_targets(ctx: dict) -> dict:
    cfg = ctx["config"]
    agent_id = resolve_default_agent_id(cfg)
    workspace_dir = resolve_agent_workspace_dir(cfg, agent_id)
    configured_agent_dir = (resolve_agent_config(cfg, agent_id).get("agentDir") or "").strip() if resolve_agent_config(cfg, agent_id) else ""
    agent_runtime = (ctx.get("runtime") or {}).get("agent") or {}
    agent_dir = (
        agent_runtime.get("resolveAgentDir", lambda c, a: None)(cfg, agent_id)
        or (resolve_home_path(configured_agent_dir) if configured_agent_dir else None)
        or os.path.join(ctx["stateDir"], "agents", agent_id, "agent")
    )
    return {"workspaceDir": workspace_dir, "agentDir": agent_dir}
