from .apply import apply_codex_migration_plan, prepare_target_codex_app_server
from .plan import build_codex_migration_plan
from .source import discover_codex_source, has_codex_source


def build_codex_migration_provider(params: dict = None) -> dict:
    params = params or {}
    runtime = params.get("runtime")

    async def detect(ctx: dict) -> dict:
        source = await discover_codex_source({"input": ctx.get("source")})
        found = has_codex_source(source)
        return {
            "found": found,
            "source": source["root"],
            "label": "Codex",
            "confidence": source["confidence"] if found else "low",
            "message": "Codex state found." if found else "Codex state not found.",
        }

    async def apply(ctx: dict, plan=None) -> dict:
        return await apply_codex_migration_plan({"ctx": ctx, "plan": plan, "runtime": runtime})

    return {
        "id": "codex",
        "label": "Codex",
        "description": "Inventory and promote Codex CLI skills while keeping Codex native plugins and hooks explicit.",
        "detect": detect,
        "plan": build_codex_migration_plan,
        "prepareApply": prepare_target_codex_app_server,
        "apply": apply,
    }
