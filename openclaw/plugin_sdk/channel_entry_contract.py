"""Channel entry contracts validate plugin channel entrypoints and runtime API facades.

Mirrors src/plugin-sdk/channel-entry-contract.ts with Python import resolution instead
of filesystem boundary loading.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path
from typing import Any

from openclaw.plugin_sdk.lazy_value import create_cached_lazy_value_getter
from openclaw.plugin_sdk.plugin_entry import (
    OpenClawPluginApi,
    empty_plugin_config_schema,
)

__all__ = [
    "BundledChannelEntryContract",
    "define_bundled_channel_entry",
    "load_bundled_entry_export",
]


@dataclass(frozen=True)
class BundledEntryModuleRef:
    specifier: str
    export_name: str | None = None


@dataclass
class BundledChannelEntryContract:
    """Runtime contract returned by a bundled channel's main entrypoint definition."""

    kind: str
    id: str
    name: str
    description: str
    register: Callable[[OpenClawPluginApi], None]
    load_channel_plugin: Callable[[], Any]
    _get_config_schema: Callable[[], Any] = field(repr=False)
    features: Mapping[str, bool] | None = None
    load_channel_outbound: Callable[[], Any] | None = None
    load_channel_secrets: Callable[[], Any] | None = None
    load_channel_account_inspector: Callable[[], Any] | None = None
    set_channel_runtime: Callable[[Any], None] | None = None

    @property
    def config_schema(self) -> Any:
        return self._get_config_schema()


def _infer_package_name(import_meta_path: Path) -> str:
    parts = import_meta_path.resolve().parts
    try:
        root_index = parts.index("openclaw_extensions")
    except ValueError:
        return import_meta_path.parent.name
    return ".".join(parts[root_index:-1])


def _resolve_bundled_entry_module_name(import_meta_path: Path, specifier: str) -> str:
    if not specifier.startswith("./"):
        return specifier
    relative = specifier[2:]
    stem = Path(relative).stem
    module_name = stem.replace("-", "_")
    return f"{_infer_package_name(import_meta_path)}.{module_name}"


def load_bundled_entry_export(
    import_meta_path: Path,
    reference: BundledEntryModuleRef | Mapping[str, str],
) -> Any:
    """Load one export from a bundled channel sidecar module."""
    if isinstance(reference, Mapping):
        ref = BundledEntryModuleRef(
            specifier=str(reference["specifier"]),
            export_name=reference.get("export_name") or reference.get("exportName"),
        )
    else:
        ref = reference

    module_name = _resolve_bundled_entry_module_name(import_meta_path, ref.specifier)
    loaded = import_module(module_name)
    if not ref.export_name:
        return getattr(loaded, "default", loaded)
    if not hasattr(loaded, ref.export_name):
        raise AttributeError(
            f"missing export {ref.export_name!r} from bundled entry module {ref.specifier}"
        )
    return getattr(loaded, ref.export_name)


def define_bundled_channel_entry(
    *,
    id: str,
    name: str,
    description: str,
    import_meta_path: Path,
    plugin: BundledEntryModuleRef | Mapping[str, str],
    outbound: BundledEntryModuleRef | Mapping[str, str] | None = None,
    secrets: BundledEntryModuleRef | Mapping[str, str] | None = None,
    config_schema: Any | Callable[[], Any] | None = None,
    runtime: BundledEntryModuleRef | Mapping[str, str] | None = None,
    account_inspect: BundledEntryModuleRef | Mapping[str, str] | None = None,
    features: Mapping[str, bool] | None = None,
    register_cli_metadata: Callable[[OpenClawPluginApi], None] | None = None,
    register_full: Callable[[OpenClawPluginApi], None] | None = None,
) -> BundledChannelEntryContract:
    """Define the full bundled channel entry contract used by core plugin registration."""
    get_config_schema = create_cached_lazy_value_getter(
        config_schema if config_schema is not None else empty_plugin_config_schema
    )

    def load_channel_plugin() -> Any:
        return load_bundled_entry_export(import_meta_path, plugin)

    load_channel_outbound = (
        (lambda: load_bundled_entry_export(import_meta_path, outbound)) if outbound else None
    )
    load_channel_secrets = (
        (lambda: load_bundled_entry_export(import_meta_path, secrets)) if secrets else None
    )
    load_channel_account_inspector = (
        (lambda: load_bundled_entry_export(import_meta_path, account_inspect))
        if account_inspect
        else None
    )

    set_channel_runtime: Callable[[Any], None] | None = None
    if runtime is not None:

        def _set_channel_runtime(plugin_runtime: Any) -> None:
            setter = load_bundled_entry_export(import_meta_path, runtime)
            setter(plugin_runtime)

        set_channel_runtime = _set_channel_runtime

    merged_features = dict(features or {})
    if account_inspect is not None:
        merged_features["account_inspect"] = True

    def register(api: OpenClawPluginApi) -> None:
        registration_mode = getattr(api, "registration_mode", None)
        if registration_mode == "cli-metadata":
            if register_cli_metadata is not None:
                register_cli_metadata(api)
            return
        if registration_mode == "tool-discovery":
            if register_full is not None:
                register_full(api)
            return

        channel_plugin = load_channel_plugin()
        register_channel = getattr(api, "register_channel", None)
        if callable(register_channel):
            register_channel({"plugin": channel_plugin})
        if set_channel_runtime is not None:
            set_channel_runtime(getattr(api, "runtime", None))
        if registration_mode == "discovery":
            if register_cli_metadata is not None:
                register_cli_metadata(api)
            return
        if registration_mode not in (None, "full"):
            return
        if register_cli_metadata is not None:
            register_cli_metadata(api)
        if register_full is not None:
            register_full(api)

    return BundledChannelEntryContract(
        kind="bundled-channel-entry",
        id=id,
        name=name,
        description=description,
        register=register,
        load_channel_plugin=load_channel_plugin,
        _get_config_schema=get_config_schema,
        features=merged_features or None,
        load_channel_outbound=load_channel_outbound,
        load_channel_secrets=load_channel_secrets,
        load_channel_account_inspector=load_channel_account_inspector,
        set_channel_runtime=set_channel_runtime,
    )
