"""Final doctor config-write decision after preview/repair mode has collected mutations."""

from __future__ import annotations

from typing import Any, Callable


async def finalize_doctor_config_flow(
    cfg: dict[str, Any],
    candidate: dict[str, Any],
    pending_changes: bool,
    should_repair: bool,
    fix_hints: list[str],
    confirm: Callable[[dict[str, Any]], Any],
    note: Callable[..., None],
) -> dict[str, Any]:
    """Decide whether doctor should write the repaired candidate config or only print hints.

    Returns a dict with 'cfg' and 'shouldWriteConfig'.
    """
    if not should_repair and pending_changes:
        should_apply = await confirm({
            "message": "Apply recommended config repairs now?",
            "initialValue": True,
        })
        if should_apply:
            return {"cfg": candidate, "shouldWriteConfig": True}
        if fix_hints:
            note("\n".join(fix_hints), "Doctor")
        return {"cfg": cfg, "shouldWriteConfig": False}

    if should_repair and pending_changes:
        return {"cfg": cfg, "shouldWriteConfig": True}

    return {"cfg": cfg, "shouldWriteConfig": False}
