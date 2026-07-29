from .plugin_registration import (
    browserPluginNodeHostCommands,
    browserPluginReload,
    browserSecurityAuditCollectors,
    register_browser_plugin,
)

plugin_entry: dict = {
    "id": "browser",
    "name": "Browser",
    "description": "Default browser tool plugin",
    "reload": browserPluginReload,
    "nodeHostCommands": browserPluginNodeHostCommands,
    "securityAuditCollectors": list(browserSecurityAuditCollectors),
    "register": register_browser_plugin,
}
