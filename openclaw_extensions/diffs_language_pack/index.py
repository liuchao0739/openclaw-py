"""Diffs Language Pack plugin entrypoint registers its OpenClaw integration."""

from openclaw_extensions.diffs_language_pack.api import define_plugin_entry
from openclaw_extensions.diffs_language_pack.src.plugin import register_diffs_language_pack_plugin

default = define_plugin_entry(
    id="diffs-language-pack",
    name="Diff Viewer Language Pack",
    description="Adds syntax highlighting for languages outside the default diffs viewer set.",
    register=register_diffs_language_pack_plugin,
)