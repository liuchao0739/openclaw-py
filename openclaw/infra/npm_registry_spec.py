from __future__ import annotations

import re
from typing import TypedDict

from openclaw_packages.normalization_core import normalize_lowercase_string_or_empty

_EXACT_SEMVER_VERSION_RE = re.compile(
    r"^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z.-]+))?(?:\+([0-9A-Za-z.-]+))?$"
)
_DIST_TAG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_UNSCOPED_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-._~]*$")
_SCOPED_NAME_RE = re.compile(r"^@[a-z0-9][a-z0-9-._~]*/[a-z0-9][a-z0-9-._~]*$")


class ParsedRegistryNpmSpec(TypedDict):
    name: str
    raw: str
    selector: str | None
    selectorKind: str
    selectorIsPrerelease: bool


def _is_openclaw_stable_correction_version(value: str) -> bool:
    return False


def _parse_registry_npm_spec_internal(
    raw_spec: str,
) -> tuple[bool, ParsedRegistryNpmSpec | str]:
    spec = raw_spec.strip()
    if not spec:
        return False, "missing npm spec"
    if re.search(r"\s", spec):
        return False, "unsupported npm spec: whitespace is not allowed"
    if "://" in spec:
        return False, "unsupported npm spec: URLs are not allowed"
    if "#" in spec:
        return False, "unsupported npm spec: git refs are not allowed"
    if ":" in spec:
        return False, "unsupported npm spec: protocol specs are not allowed"

    at = spec.rfind("@")
    has_selector = at > 0
    name = spec[:at] if has_selector else spec
    selector = spec[at + 1:] if has_selector else ""

    is_valid_name = (
        _SCOPED_NAME_RE.match(name) if name.startswith("@") else _UNSCOPED_NAME_RE.match(name)
    )
    if not is_valid_name:
        return (
            False,
            "unsupported npm spec: expected <name> or <name>@<version> from the npm registry",
        )

    if not has_selector:
        return (
            True,
            {
                "name": name,
                "raw": spec,
                "selector": None,
                "selectorKind": "none",
                "selectorIsPrerelease": False,
            },
        )

    if not selector:
        return False, "unsupported npm spec: missing version/tag after @"

    if re.search(r"[\\/]", selector):
        return False, "unsupported npm spec: invalid version/tag"

    exact_version_match = _EXACT_SEMVER_VERSION_RE.match(selector)
    if exact_version_match:
        return (
            True,
            {
                "name": name,
                "raw": spec,
                "selector": selector,
                "selectorKind": "exact-version",
                "selectorIsPrerelease": bool(exact_version_match.group(4))
                and not _is_openclaw_stable_correction_version(selector),
            },
        )

    if not _DIST_TAG_RE.match(selector):
        return (
            False,
            "unsupported npm spec: use an exact version or dist-tag (ranges are not allowed)",
        )

    return (
        True,
        {
            "name": name,
            "raw": spec,
            "selector": selector,
            "selectorKind": "tag",
            "selectorIsPrerelease": False,
        },
    )


def parse_registry_npm_spec(raw_spec: str) -> ParsedRegistryNpmSpec | None:
    ok, result = _parse_registry_npm_spec_internal(raw_spec)
    return result if ok else None


def is_openclaw_org_npm_spec(raw_spec: str | None) -> bool:
    parsed = parse_registry_npm_spec(raw_spec) if raw_spec else None
    return parsed is not None and parsed["name"].startswith("@openclaw/")


def validate_registry_npm_spec(raw_spec: str) -> str | None:
    ok, result = _parse_registry_npm_spec_internal(raw_spec)
    return None if ok else result


def is_exact_semver_version(value: str) -> bool:
    return bool(_EXACT_SEMVER_VERSION_RE.match(value.strip()))


__all__ = [
    "ParsedRegistryNpmSpec",
    "is_exact_semver_version",
    "is_openclaw_org_npm_spec",
    "parse_registry_npm_spec",
    "validate_registry_npm_spec",
]
