"""Diffs plugin entrypoint registers its OpenClaw integration."""

from openclaw_extensions.diffs.api import define_plugin_entry
from openclaw_extensions.diffs.src.config import diffs_plugin_config_schema
from openclaw_extensions.diffs.src.plugin import register_diffs_plugin

default = define_plugin_entry(
    id="diffs",
    name="Diffs",
    description="Read-only diff viewer and PNG/PDF renderer for agents.",
    config_schema=diffs_plugin_config_schema,
    register=register_diffs_plugin,
)
