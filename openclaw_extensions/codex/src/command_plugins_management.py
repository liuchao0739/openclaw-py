from .command_formatters import format_codex_display_text
from .command_presentation import build_codex_command_picker_presentation

POLICY_REFRESH_HINT = "New Codex conversations pick this up automatically. Use /new or /reset to refresh the current one."


async def handle_codex_plugins_subcommand(ctx: dict, rest: list, io: dict) -> dict:
    verb = rest[0] if rest else "list"
    args = rest[1:]
    normalized = verb.lower()
    if normalized == "menu":
        if args:
            return {"text": "Usage: /codex plugins menu"}
        return _build_plugins_menu_reply()
    if normalized == "help":
        if args:
            return {"text": "Usage: /codex plugins help"}
        return {"text": build_plugins_help()}
    if normalized == "list":
        if args:
            return {"text": "Usage: /codex plugins list"}
        current = await io["readConfig"]()
        return {"text": format_plugin_list(current.get("plugins") or {}, {"globalEnabled": current.get("enabled") is True})}
    target = args[0] if args else None
    if normalized in ("enable", "disable"):
        if not args:
            current = await io["readConfig"]()
            return _build_plugin_name_picker_reply(normalized, current)
        if not target or len(args) > 1:
            return {"text": f"Usage: /codex plugins {normalized} <name>"}
        if not _can_mutate_codex_plugins(ctx):
            return {"text": f"Only an owner or operator.admin gateway client can run /codex plugins {normalized}."}
        want_enabled = normalized == "enable"
        current_plugins = (await io["readConfig"]()).get("plugins") or {}
        if target not in current_plugins:
            return {"text": f"Codex sub-plugin '{format_codex_display_text(target)}' is not configured. Run '/codex plugins list' to see configured plugins."}

        def update(block):
            if want_enabled:
                block["enabled"] = True
            block.setdefault("plugins", {})
            block["plugins"][target] = {**block["plugins"].get(target, {}), "enabled": want_enabled}

        await io["mutate"](update)
        return {"text": f"{format_codex_display_text(target)}: {'enabled' if want_enabled else 'disabled'} in openclaw.json. {POLICY_REFRESH_HINT}"}
    return {"text": f"Unknown /codex plugins subcommand: {format_codex_display_text(verb)}\n\n{build_plugins_help()}"}


def _build_plugins_menu_reply() -> dict:
    buttons = [
        {"label": "list", "command": "/codex plugins list"},
        {"label": "enable", "command": "/codex plugins enable"},
        {"label": "disable", "command": "/codex plugins disable"},
        {"label": "help", "command": "/codex plugins help"},
        {"label": "back", "command": "/codex"},
    ]
    text = "\n".join([
        "Codex sub-plugins. Pick a sub-action or type:",
        "",
        "  1. /codex plugins list",
        "  2. /codex plugins enable",
        "  3. /codex plugins disable",
        "  4. /codex plugins help",
        "",
        "Type '/codex' to go back to the main menu.",
    ])
    return {
        "text": text,
        "presentation": build_codex_command_picker_presentation("Codex sub-plugins", "Pick a Codex sub-plugin action:", buttons),
    }


def _build_plugin_name_picker_reply(verb: str, current: dict) -> dict:
    global_enabled = current.get("enabled") is True
    entries = sorted((current.get("plugins") or {}).items(), key=lambda kv: kv[0])
    eligible = []
    for key, entry in entries:
        effectively_enabled = global_enabled and entry.get("enabled") is not False
        if verb == "disable":
            if effectively_enabled:
                eligible.append((key, entry))
        else:
            if not effectively_enabled:
                eligible.append((key, entry))
    if not eligible:
        action = "disabled" if verb == "enable" else "enabled"
        return {
            "text": "\n".join([
                f"No configured {action} Codex sub-plugins found.",
                "",
                "Type '/codex plugins list' to inspect configured sub-plugins.",
                "Type '/codex plugins menu' to go back to the plugins menu.",
            ]),
            "presentation": build_codex_command_picker_presentation(
                "Codex sub-plugins",
                "Pick another Codex sub-plugin action:",
                [
                    {"label": "list", "command": "/codex plugins list"},
                    {"label": "back", "command": "/codex plugins menu"},
                ],
            ),
        }
    buttons = [
        *[{"label": format_codex_display_text(key), "command": f"/codex plugins {verb} {key}"} for key, _ in eligible],
        {"label": "back", "command": "/codex plugins menu"},
    ]
    lines = [
        f"Codex sub-plugins to {verb}. Pick one or type:",
        "",
        *[f"  {index + 1}. /codex plugins {verb} {key}" for index, (key, _) in enumerate(eligible)],
        "",
    ]
    if verb == "enable" and not global_enabled:
        lines.extend(["Global codexPlugins.enabled is off; enabling one configured sub-plugin turns it on.", ""])
    lines.append("Type '/codex plugins menu' to go back to the plugins menu.")
    return {
        "text": "\n".join(lines),
        "presentation": build_codex_command_picker_presentation("Codex sub-plugins", f"Pick a Codex sub-plugin to {verb}:", buttons),
    }


def _can_mutate_codex_plugins(ctx: dict) -> bool:
    if ctx.get("senderIsOwner") is True:
        return True
    return "operator.admin" in (ctx.get("gatewayClientScopes") or [])


def build_plugins_help() -> str:
    return "\n".join([
        "Codex sub-plugin management (writes only to ~/.openclaw/openclaw.json, never to ~/.codex/config.toml):",
        "- /codex plugins                  (alias for list)",
        "- /codex plugins list             show all configured Codex sub-plugins",
        "- /codex plugins enable <name>    enable a configured sub-plugin",
        "- /codex plugins disable <name>   disable a configured sub-plugin",
    ])


def format_plugin_list(plugins: dict, options: dict = None) -> str:
    options = options or {}
    global_enabled = options.get("globalEnabled") is True
    keys = sorted(plugins.keys())
    if not keys:
        return "No Codex sub-plugins configured under plugins.entries.codex.config.codexPlugins.plugins"
    rows = []
    for key in keys:
        entry = plugins.get(key) or {}
        state = "ON " if global_enabled and entry.get("enabled") is not False else "OFF"
        display_key = format_codex_display_text(key)
        plugin_name = format_codex_display_text(entry.get("pluginName") or key)
        marketplace = format_codex_display_text(entry.get("marketplaceName") or "?")
        rows.append({"displayKey": display_key, "state": state, "pluginName": plugin_name, "marketplace": marketplace})
    key_w = max(len(r["displayKey"]) for r in rows)
    plugin_w = max(len(r["pluginName"]) for r in rows)
    lines = [
        "Codex sub-plugins in Openclaw config (~/.openclaw/openclaw.json):",
        "",
        *[f"  {r['state']}  {r['displayKey'].ljust(key_w)}  {r['pluginName'].ljust(plugin_w)}  [{r['marketplace']}]" for r in rows],
        "",
    ]
    if not global_enabled:
        lines.extend(["Global codexPlugins.enabled is off; configured sub-plugins are inactive.", ""])
    lines.append("New Codex conversations pick up policy changes automatically; /new or /reset to refresh the current one.")
    return "\n".join(lines)
