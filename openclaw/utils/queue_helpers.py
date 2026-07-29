from __future__ import annotations

import asyncio
import os
import time
from typing import Any, Callable


def clear_queue_summary_state(state: dict) -> None:
    state["droppedCount"] = 0
    state["summaryLines"] = []


def preview_queue_summary_prompt(params: dict) -> str | None:
    return _build_queue_summary_prompt(
        {
            "state": {
                "dropPolicy": params["state"].get("dropPolicy"),
                "droppedCount": params["state"].get("droppedCount", 0),
                "summaryLines": list(params["state"].get("summaryLines", [])),
            },
            "noun": params["noun"],
            "title": params.get("title"),
        }
    )


def apply_queue_runtime_settings(params: dict) -> None:
    target = params["target"]
    settings = params["settings"]
    target["mode"] = settings["mode"]
    debounce_ms = settings.get("debounceMs")
    target["debounceMs"] = (
        max(0, debounce_ms) if isinstance(debounce_ms, (int, float)) else target["debounceMs"]
    )
    cap = settings.get("cap")
    target["cap"] = max(0, int(cap)) if isinstance(cap, (int, float)) and cap > 0 else target["cap"]
    drop_policy = settings.get("dropPolicy")
    target["dropPolicy"] = drop_policy if drop_policy is not None else target["dropPolicy"]


def _elide_queue_text(text: str, limit: int = 140) -> str:
    if len(text) <= limit:
        return text
    return f"{text[: max(0, limit - 1)].rstrip()}…"


def _build_queue_summary_line(text: str, limit: int = 160) -> str:
    import re

    cleaned = re.sub(r"\s+", " ", text).strip()
    return _elide_queue_text(cleaned, limit)


def should_skip_queue_item(params: dict) -> bool:
    dedupe = params.get("dedupe")
    if not dedupe:
        return False
    return dedupe(params["item"], params["items"])


def apply_queue_drop_policy(params: dict) -> bool:
    queue = params["queue"]
    cap = queue.get("cap", 0)
    if cap <= 0 or len(queue["items"]) < cap:
        return True
    if queue["dropPolicy"] == "new":
        return False
    drop_count = len(queue["items"]) - cap + 1
    dropped = queue["items"][:drop_count]
    del queue["items"][:drop_count]
    on_drop = params.get("onDrop")
    if on_drop:
        on_drop(dropped)
    if queue["dropPolicy"] == "summarize":
        summarize = params["summarize"]
        for item in dropped:
            queue["droppedCount"] += 1
            queue["summaryLines"].append(_build_queue_summary_line(summarize(item)))
        limit = max(0, params.get("summaryLimit", cap))
        while len(queue["summaryLines"]) > limit:
            queue["summaryLines"].pop(0)
    return True


async def wait_for_queue_debounce(queue: dict) -> None:
    if os.environ.get("OPENCLAW_TEST_FAST") == "1":
        return
    debounce_ms = max(0, queue.get("debounceMs", 0))
    if debounce_ms <= 0:
        return

    while True:
        since = time.time() * 1000 - queue.get("lastEnqueuedAt", 0)
        if since >= debounce_ms:
            return
        await asyncio.sleep((debounce_ms - since) / 1000.0)


def begin_queue_drain(map_: dict, key: str) -> dict | None:
    queue = map_.get(key)
    if not queue or queue.get("draining"):
        return None
    queue["draining"] = True
    return queue


def remove_queued_items_by_ref(items: list, processed: list) -> None:
    for item in processed:
        try:
            items.remove(item)
        except ValueError:
            pass


async def drain_next_queue_item(items: list, run: Callable) -> bool:
    if not items:
        return False
    next_item = items[0]
    await run(next_item)
    remove_queued_items_by_ref(items, [next_item])
    return True


async def _drain_collect_item_if_needed(params: dict) -> str:
    if not params["forceIndividualCollect"] and not params["isCrossChannel"]:
        return "skipped"
    if params["isCrossChannel"]:
        setter = params.get("setForceIndividualCollect")
        if setter:
            setter(True)
    drained = await drain_next_queue_item(params["items"], params["run"])
    return "drained" if drained else "empty"


async def drain_collect_queue_step(params: dict) -> str:
    return await _drain_collect_item_if_needed(
        {
            "forceIndividualCollect": params["collectState"]["forceIndividualCollect"],
            "isCrossChannel": params["isCrossChannel"],
            "setForceIndividualCollect": lambda next_val: params["collectState"].__setitem__(
                "forceIndividualCollect", next_val
            ),
            "items": params["items"],
            "run": params["run"],
        }
    )


def _build_queue_summary_prompt(params: dict) -> str | None:
    state = params["state"]
    if state.get("dropPolicy") != "summarize" or state.get("droppedCount", 0) <= 0:
        return None
    noun = params["noun"]
    dropped_count = state["droppedCount"]
    title = params.get("title") or (
        f"[Queue overflow] Dropped {dropped_count} {noun}{'s' if dropped_count != 1 else ''} due to cap."
    )
    lines = [title]
    summary_lines = state.get("summaryLines", [])
    if summary_lines:
        lines.append("Summary:")
        for line in summary_lines:
            lines.append(f"- {line}")
    clear_queue_summary_state(state)
    return "\n".join(lines)


def build_collect_prompt(params: dict) -> str:
    blocks: list[str] = [params["title"]]
    if params.get("summary"):
        blocks.append(params["summary"])
    render_item = params["renderItem"]
    for idx, item in enumerate(params["items"]):
        blocks.append(render_item(item, idx))
    return "\n\n".join(blocks)


def has_cross_channel_items(items: list, resolve_key: Callable) -> bool:
    keys: set[str] = set()
    for item in items:
        resolved = resolve_key(item)
        if resolved.get("cross"):
            return True
        key = resolved.get("key")
        if not key:
            continue
        keys.add(key)
    return len(keys) > 1
