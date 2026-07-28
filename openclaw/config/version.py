from __future__ import annotations

import re
from typing import Optional


def _normalize_legacy_dot_beta_version(raw: str) -> str:
    return re.sub(r"(\d+)\.(\d+)-beta\.(\d+)", r"\1.\2.0-beta.\3", raw)


def _compare_prerelease_identifiers(a: list[str] | None, b: list[str] | None) -> int:
    if not a and not b:
        return 0
    if not a:
        return 1
    if not b:
        return -1
    for x, y in zip(a, b):
        if x < y:
            return -1
        if x > y:
            return 1
    return len(a) - len(b)


def parse_openclaw_version(raw: str | None) -> dict | None:
    if not raw:
        return None
    normalized = _normalize_legacy_dot_beta_version(raw.strip())
    m = re.match(r"^v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$", normalized)
    if not m:
        return None
    major, minor, patch, suffix = m.groups()
    revision = None
    if suffix and re.match(r"^[0-9]+$", suffix):
        revision = int(suffix)
    prerelease = None
    if suffix and revision is None:
        prerelease = [p for p in suffix.split(".") if p]
    return {
        "major": int(major),
        "minor": int(minor),
        "patch": int(patch),
        "revision": revision,
        "prerelease": prerelease,
    }


def normalize_openclaw_version_base(raw: str | None) -> str | None:
    parsed = parse_openclaw_version(raw)
    if not parsed:
        return None
    return f"{parsed['major']}.{parsed['minor']}.{parsed['patch']}"


def is_same_openclaw_stable_family(a: str | None, b: str | None) -> bool:
    pa = parse_openclaw_version(a)
    pb = parse_openclaw_version(b)
    if not pa or not pb:
        return False
    if pa.get("prerelease") or pb.get("prerelease"):
        return False
    return pa["major"] == pb["major"] and pa["minor"] == pb["minor"] and pa["patch"] == pb["patch"]


def _release_rank(version: dict) -> int:
    if version.get("prerelease"):
        return 0
    if version.get("revision") is not None:
        return 2
    return 1


def compare_openclaw_versions(a: str | None, b: str | None) -> int | None:
    pa = parse_openclaw_version(a)
    pb = parse_openclaw_version(b)
    if not pa or not pb:
        return None
    for key in ("major", "minor", "patch"):
        if pa[key] != pb[key]:
            return -1 if pa[key] < pb[key] else 1
    rank_a = _release_rank(pa)
    rank_b = _release_rank(pb)
    if rank_a != rank_b:
        return -1 if rank_a < rank_b else 1
    if pa.get("revision") is not None and pb.get("revision") is not None:
        if pa["revision"] != pb["revision"]:
            return -1 if pa["revision"] < pb["revision"] else 1
    if pa.get("prerelease") or pb.get("prerelease"):
        return _compare_prerelease_identifiers(pa.get("prerelease"), pb.get("prerelease"))
    return 0


def should_warn_on_touched_version(current: str | None, touched: str | None) -> bool:
    pc = parse_openclaw_version(current)
    pt = parse_openclaw_version(touched)
    if pc and pt and pc["major"] == pt["major"] and pc["minor"] == pt["minor"] and pc["patch"] == pt["patch"]:
        if not pt.get("prerelease"):
            return False
    if is_same_openclaw_stable_family(current, touched):
        return False
    cmp_result = compare_openclaw_versions(current, touched)
    return cmp_result is not None and cmp_result < 0
