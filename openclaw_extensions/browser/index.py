"""Browser plugin entry."""

from __future__ import annotations

from openclaw.plugin_sdk.plugin_entry import define_plugin_entry
from openclaw_extensions.browser.plugin_registration import (
    browser_plugin_node_host_commands,
    browser_plugin_reload,
    browser_security_audit_collectors,
    register_browser_plugin,
)

default = define_plugin_entry(
    id="browser",
    name="Browser",
    description="Default browser tool plugin",
    reload=browser_plugin_reload,
    node_host_commands=browser_plugin_node_host_commands,
    security_audit_collectors=list(browser_security_audit_collectors),
    register=register_browser_plugin,
)
