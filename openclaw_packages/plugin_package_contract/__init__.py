"""External code plugin package.json compatibility and validation contracts.

Mirrors packages/plugin-package-contract/src/index.ts.
"""

from __future__ import annotations

from typing import Any, TypedDict

from openclaw.packages.normalization_core import is_record, normalize_optional_string

JsonObject = dict[str, Any]


class ExternalPluginCompatibility(TypedDict, total=False):
    plugin_api_range: str
    built_with_openclaw_version: str
    plugin_sdk_version: str
    min_gateway_version: str


class ExternalPluginValidationIssue(TypedDict):
    field_path: str
    message: str


class ExternalCodePluginValidationResult(TypedDict, total=False):
    compatibility: ExternalPluginCompatibility
    issues: list[ExternalPluginValidationIssue]


EXTERNAL_CODE_PLUGIN_REQUIRED_FIELD_PATHS: tuple[str, ...] = (
    "openclaw.compat.pluginApi",
    "openclaw.build.openclawVersion",
)


def _read_openclaw_block(package_json: Any) -> dict[str, Any | None]:
    root = package_json if is_record(package_json) else None
    openclaw = root.get("openclaw") if root and is_record(root.get("openclaw")) else None
    compat = openclaw.get("compat") if openclaw and is_record(openclaw.get("compat")) else None
    build = openclaw.get("build") if openclaw and is_record(openclaw.get("build")) else None
    install = openclaw.get("install") if openclaw and is_record(openclaw.get("install")) else None
    return {
        "root": root,
        "openclaw": openclaw,
        "compat": compat,
        "build": build,
        "install": install,
    }


def normalize_external_plugin_compatibility(
    package_json: Any,
) -> ExternalPluginCompatibility | None:
    """Normalize compatibility metadata from an external plugin package.json."""
    blocks = _read_openclaw_block(package_json)
    root = blocks["root"]
    compat = blocks["compat"]
    build = blocks["build"]
    install = blocks["install"]

    version = normalize_optional_string(root.get("version") if root else None)
    min_host_version = normalize_optional_string(
        install.get("minHostVersion") if install else None
    )
    compatibility: ExternalPluginCompatibility = {}

    plugin_api = normalize_optional_string(compat.get("pluginApi") if compat else None)
    if plugin_api:
        compatibility["plugin_api_range"] = plugin_api

    min_gateway_version = normalize_optional_string(
        compat.get("minGatewayVersion") if compat else None
    ) or min_host_version
    if min_gateway_version:
        compatibility["min_gateway_version"] = min_gateway_version

    built_with_openclaw_version = normalize_optional_string(
        build.get("openclawVersion") if build else None
    ) or version
    if built_with_openclaw_version:
        compatibility["built_with_openclaw_version"] = built_with_openclaw_version

    plugin_sdk_version = normalize_optional_string(
        build.get("pluginSdkVersion") if build else None
    )
    if plugin_sdk_version:
        compatibility["plugin_sdk_version"] = plugin_sdk_version

    return compatibility or None


def list_missing_external_code_plugin_field_paths(package_json: Any) -> list[str]:
    """List missing required field paths for an external code plugin package.json."""
    blocks = _read_openclaw_block(package_json)
    compat = blocks["compat"]
    build = blocks["build"]
    missing: list[str] = []
    if not normalize_optional_string(compat.get("pluginApi") if compat else None):
        missing.append("openclaw.compat.pluginApi")
    if not normalize_optional_string(build.get("openclawVersion") if build else None):
        missing.append("openclaw.build.openclawVersion")
    return missing


def validate_external_code_plugin_package_json(
    package_json: Any,
) -> ExternalCodePluginValidationResult:
    """Validate an external code plugin package.json against required compatibility fields."""
    issues: list[ExternalPluginValidationIssue] = [
        {
            "field_path": field_path,
            "message": f"{field_path} is required for external code plugin packages.",
        }
        for field_path in list_missing_external_code_plugin_field_paths(package_json)
    ]
    result: ExternalCodePluginValidationResult = {"issues": issues}
    compatibility = normalize_external_plugin_compatibility(package_json)
    if compatibility:
        result["compatibility"] = compatibility
    return result


__all__ = [
    "EXTERNAL_CODE_PLUGIN_REQUIRED_FIELD_PATHS",
    "ExternalCodePluginValidationResult",
    "ExternalPluginCompatibility",
    "ExternalPluginValidationIssue",
    "JsonObject",
    "list_missing_external_code_plugin_field_paths",
    "normalize_external_plugin_compatibility",
    "validate_external_code_plugin_package_json",
]
