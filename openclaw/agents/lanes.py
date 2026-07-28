from __future__ import annotations

from typing import Any


def build_lanes() -> dict[str, Any]:
    return {
        "lanes": {},
        "activeLane": None,
    }


def resolve_lane(
    lanes: dict[str, Any],
    lane_id: str,
) -> dict[str, Any] | None:
    return lanes.get("lanes", {}).get(lane_id)
