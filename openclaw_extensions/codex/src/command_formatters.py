import re
from typing import Any, List, Optional

CODEX_RESUME_SAFE_THREAD_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]+$")
EMAIL_PATTERN = re.compile(r"[^\s@<>()\[\]`]+@[^\s@<>()\[\]`]+\.[^\s@<>()\[\]`]+")
LIKELY_EMAIL_PATTERN = re.compile(r"^[^\s@<>()\[\]`]+@[^\s@<>()\[\]`]+\.[^\s@<>()\[\]`]+$")


def format_codex_status(probes: dict) -> str:
    connected = (
        probes["models"]["ok"]
        or probes["account"]["ok"]
        or probes["limits"]["ok"]
        or probes["mcps"]["ok"]
        or probes["skills"]["ok"]
    )
    lines = [f"Codex app-server: {'connected' if connected else 'unavailable'}"]
    if probes["models"]["ok"]:
        model_ids = [format_codex_display_text(model["id"]) for model in probes["models"]["value"]["models"]][:8]
        lines.append(f"Models: {', '.join(model_ids) or 'none'}")
    else:
        lines.append(f"Models: {format_codex_display_text(probes['models']['error'])}")
    lines.append(f"Account: {format_codex_account_summary(probes['account']['value']) if probes['account']['ok'] else format_codex_display_text(probes['account']['error'])}")
    lines.append(f"Rate limits: {format_codex_rate_limit_summary(probes['limits']['value']) if probes['limits']['ok'] else format_codex_display_text(probes['limits']['error'])}")
    lines.append(f"MCP servers: {summarize_array_like(probes['mcps']['value']) if probes['mcps']['ok'] else format_codex_display_text(probes['mcps']['error'])}")
    lines.append(f"Skills: {summarize_codex_skills(probes['skills']['value']) if probes['skills']['ok'] else format_codex_display_text(probes['skills']['error'])}")
    return "\n".join(lines)


def format_models(result: dict) -> str:
    if not result["models"]:
        return "No Codex app-server models returned."
    lines = ["Codex models:"]
    for model in result["models"]:
        suffix = " (default)" if model.get("isDefault") else ""
        lines.append(f"- {format_codex_display_text(model['id'])}{suffix}")
    if result.get("truncated"):
        lines.append("- More models available; output truncated.")
    return "\n".join(lines)


def format_threads(response) -> str:
    threads = extract_array(response)
    if not threads:
        return "No Codex threads returned."
    lines = ["Codex threads:"]
    for thread in threads[:10]:
        record = thread if isinstance(thread, dict) else {}
        thread_id = read_string(record, "threadId") or read_string(record, "id") or "<unknown>"
        title = read_string(record, "title") or read_string(record, "name") or read_string(record, "summary")
        details = [v for v in [read_string(record, "model"), read_string(record, "cwd"), read_string(record, "updatedAt") or read_string(record, "lastUpdatedAt")] if v]
        detail_str = f" ({', '.join(format_codex_display_text(d) for d in details)})" if details else ""
        title_str = f" - {format_codex_display_text(title)}" if title else ""
        lines.append(f"- {format_codex_display_text(thread_id)}{title_str}{detail_str}\n  Resume: {format_codex_resume_hint(thread_id)}")
    return "\n".join(lines)


def format_account(account: dict, limits: dict, auth_overview: Optional[dict] = None) -> str:
    if auth_overview:
        return format_account_auth_overview(auth_overview)
    formatted_limits = format_codex_rate_limit_details(limits["value"]) if limits["ok"] else format_codex_display_text(limits["error"])
    if formatted_limits.startswith("Codex is "):
        rate_limit_block = formatted_limits
    elif "\n" in formatted_limits:
        rate_limit_block = f"Rate limits:\n{formatted_limits}"
    else:
        rate_limit_block = f"Rate limits: {formatted_limits}"
    account_str = format_codex_account_summary(account["value"]) if account["ok"] else format_codex_display_text(account["error"])
    return f"Account: {account_str}\n\n{rate_limit_block}"


def format_account_auth_overview(overview: dict) -> str:
    lines: List[str] = []
    if overview.get("currentLine"):
        lines.extend([overview["currentLine"], ""])
    if overview.get("subscriptionLabel"):
        lines.append(f"Subscription  {overview['subscriptionLabel']}")
        if overview.get("subscriptionUsage"):
            lines.append(f"  {overview['subscriptionUsage']}")
        lines.append("")
    if overview.get("rows"):
        lines.append(overview["orderTitle"])
        for index, row in enumerate(overview["rows"]):
            lines.append(f"  {index + 1}. {row['label']}   {row['kind']}   — {format_auth_row_status(row)}")
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(format_codex_account_line(line) for line in lines)


def format_auth_row_status(row: dict) -> str:
    return f"{row['status']} · {row['billingNote']}" if row.get("billingNote") else row["status"]


def format_computer_use_status(status: dict) -> str:
    state = "ready" if status["ready"] else ("not ready" if status.get("enabled") else "disabled")
    lines = [f"Computer Use: {state}"]
    lines.append(f"Plugin: {format_codex_display_text(status['pluginName'])} ({computer_use_plugin_state(status)})")
    mcp_suffix = f" ({len(status['tools'])} tools)" if status.get("mcpServerAvailable") else " (unavailable)"
    lines.append(f"MCP server: {format_codex_display_text(status['mcpServerName'])}{mcp_suffix}")
    if status.get("marketplaceName"):
        lines.append(f"Marketplace: {format_codex_display_text(status['marketplaceName'])}")
    if status.get("tools"):
        lines.append(f"Tools: {', '.join(format_codex_display_text(t) for t in status['tools'][:8])}")
    lines.append(format_codex_display_text(status["message"]))
    return "\n".join(lines)


def computer_use_plugin_state(status: dict) -> str:
    if not status.get("installed"):
        return "not installed"
    return "installed" if status.get("pluginEnabled") else "installed, disabled"


def format_list(response, label: str) -> str:
    entries = extract_array(response)
    if not entries:
        return f"{label}: none returned."
    lines = [f"{label}:"]
    for entry in entries[:25]:
        record = entry if isinstance(entry, dict) else {}
        import json

        value = read_string(record, "name") or read_string(record, "id") or json.dumps(entry)
        lines.append(f"- {format_codex_display_text(value)}")
    return "\n".join(lines)


def format_skills(response) -> str:
    groups = response.get("data") if isinstance(response, dict) and isinstance(response.get("data"), list) else []
    if not groups:
        return "Codex skills: none returned."
    lines = ["Codex skills:"]
    rendered_skills = 0
    load_errors = 0
    for group in groups:
        record = group if isinstance(group, dict) else {}
        if isinstance(record.get("errors"), list):
            load_errors += len(record["errors"])
        skills = record.get("skills") if isinstance(record.get("skills"), list) else []
        if not skills:
            continue
        for skill in skills:
            if isinstance(skill, dict) and skill.get("enabled") is False:
                continue
            lines.append(f"- {format_codex_skill_entry(skill)}")
            rendered_skills += 1
    if rendered_skills == 0:
        if load_errors > 0:
            return f"Codex skills: none returned ({load_errors} load {'error' if load_errors == 1 else 'errors'})."
        return "Codex skills: none returned."
    return "\n".join(lines)


def format_codex_skill_entry(entry) -> str:
    record = entry if isinstance(entry, dict) else {}
    name = read_string(record, "name") or "<unknown>"
    return f"`{format_codex_display_text(name)}`"


def format_codex_resume_hint(thread_id: str) -> str:
    safe = format_codex_text_for_display(thread_id)
    if not CODEX_RESUME_SAFE_THREAD_ID_PATTERN.match(safe):
        return "copy the thread id above and run /codex resume <thread-id>"
    return f"/codex resume {safe}"


def format_codex_display_text(value: str) -> str:
    return escape_codex_chat_text(format_codex_text_for_display(value))


def format_codex_account_summary(value) -> str:
    safe = format_codex_text_for_display(summarize_account(value))
    if is_likely_email_address(safe):
        return escape_codex_chat_text_preserving_at(safe)
    return escape_codex_chat_text(safe)


def format_codex_text_for_display(value: str) -> str:
    safe = sanitize_codex_text_for_display(value).strip()
    return safe or "<unknown>"


def sanitize_codex_text_for_display(value: str) -> str:
    safe = ""
    for character in value:
        code_point = ord(character)
        safe += "?" if is_unsafe_display_code_point(code_point) else character
    return safe


def escape_codex_chat_text(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("@", "\uff20")
        .replace("`", "\uff40")
        .replace("[", "\uff3b")
        .replace("]", "\uff3d")
        .replace("(", "\uff08")
        .replace(")", "\uff09")
        .replace("*", "\u2217")
        .replace("_", "\uff3f")
        .replace("~", "\uff5e")
        .replace("|", "\uff5c")
    )


def escape_codex_chat_text_preserving_at(value: str) -> str:
    return escape_codex_chat_text(value).replace("\uff20", "@")


def format_codex_account_line(value: str) -> str:
    if value == "":
        return ""
    safe = sanitize_codex_text_for_display(value).rstrip()
    if not safe.strip():
        return ""
    formatted = ""
    last_index = 0
    for match in EMAIL_PATTERN.finditer(safe):
        index = match.start()
        formatted += escape_codex_chat_text(safe[last_index:index])
        formatted += escape_codex_chat_text_preserving_at(match.group(0))
        last_index = match.end()
    formatted += escape_codex_chat_text(safe[last_index:])
    return formatted


def is_likely_email_address(value: str) -> bool:
    return bool(LIKELY_EMAIL_PATTERN.match(value))


def is_unsafe_display_code_point(code_point: int) -> bool:
    return (
        code_point <= 0x001F
        or (0x007F <= code_point <= 0x009F)
        or code_point == 0x00AD
        or code_point == 0x061C
        or code_point == 0x180E
        or (0x200B <= code_point <= 0x200F)
        or (0x202A <= code_point <= 0x202E)
        or (0x2060 <= code_point <= 0x206F)
        or code_point == 0xFEFF
        or (0xFFF9 <= code_point <= 0xFFFB)
        or (0xE0000 <= code_point <= 0xE007F)
    )


def build_help() -> str:
    return "\n".join([
        "Codex commands:",
        "- /codex status",
        "- /codex models",
        "- /codex threads [filter]",
        "- /codex sessions --host <node> [filter]",
        "- /codex resume <thread-id>",
        "- /codex resume <session-id> --host <node> --bind here",
        "- /codex bind [thread-id] [--cwd <path>] [--model <model>] [--provider <provider>]",
        "- /codex binding",
        "- /codex stop",
        "- /codex steer <message>",
        "- /codex model [model]",
        "- /codex fast [on|off|status]",
        "- /codex permissions [default|yolo|status]",
        "- /codex detach",
        "- /codex compact",
        "- /codex review",
        "- /codex diagnostics [note]",
        "- /codex computer-use [status|install]",
        "- /codex account",
        "- /codex mcp",
        "- /codex skills",
        "- /codex plugins [list|enable|disable]",
    ])


def summarize_account(value) -> str:
    if not isinstance(value, dict):
        return "unavailable"
    account = value.get("account") if isinstance(value.get("account"), dict) else value
    account_type = read_string(account, "type")
    if account_type == "amazonBedrock":
        return "Amazon Bedrock"
    return (
        read_string(account, "email")
        or read_string(account, "accountEmail")
        or read_string(account, "planType")
        or read_string(account, "id")
        or "available"
    )


def summarize_array_like(value) -> str:
    entries = extract_array(value)
    if not entries:
        return "none returned"
    return str(len(entries))


def summarize_codex_skills(value) -> str:
    groups = value.get("data") if isinstance(value, dict) and isinstance(value.get("data"), list) else []
    if not groups:
        return "none returned"
    enabled_skills = 0
    load_errors = 0
    for group in groups:
        if not isinstance(group, dict):
            continue
        if isinstance(group.get("errors"), list):
            load_errors += len(group["errors"])
        if not isinstance(group.get("skills"), list):
            continue
        enabled_skills += sum(1 for skill in group["skills"] if not isinstance(skill, dict) or skill.get("enabled") is not False)
    if enabled_skills > 0:
        return str(enabled_skills)
    if load_errors > 0:
        return f"none returned ({load_errors} load {'error' if load_errors == 1 else 'errors'})"
    return "none returned"


def format_codex_rate_limit_summary(value) -> str:
    from .app_server.rate_limits import summarize_codex_rate_limits, has_codex_rate_limit_snapshots

    summary = summarize_codex_rate_limits(value)
    if summary:
        return format_codex_display_text(summary)
    return format_codex_display_text("none returned" if has_codex_rate_limit_snapshots(value) else summarize_rate_limits(value))


def format_codex_rate_limit_details(value) -> str:
    from .app_server.rate_limits import summarize_codex_account_rate_limits, has_codex_rate_limit_snapshots

    lines = summarize_codex_account_rate_limits(value)
    if not lines:
        return format_codex_display_text("none returned" if has_codex_rate_limit_snapshots(value) else summarize_rate_limits(value))
    return "\n".join(format_codex_display_text(line) for line in lines)


def summarize_rate_limits(value) -> str:
    entries = extract_array(value)
    if entries:
        count = sum(1 for entry in entries if is_meaningful_rate_limit_snapshot(entry))
        return str(count) if count > 0 else "none returned"
    if not isinstance(value, dict):
        return "none returned"
    keyed = value.get("rateLimitsByLimitId")
    if isinstance(keyed, dict):
        count = sum(1 for entry in keyed.values() if is_meaningful_rate_limit_snapshot(entry))
        if count > 0:
            return str(count)
    return "1" if is_meaningful_rate_limit_snapshot(value.get("rateLimits")) else "none returned"


def is_meaningful_rate_limit_snapshot(value) -> bool:
    if not isinstance(value, dict):
        return False
    reached_type = read_string(value, "rateLimitReachedType") or read_string(value, "rate_limit_reached_type")
    if reached_type:
        return True
    return any(
        isinstance(value.get(key), dict) and any(entry is not None for entry in value[key].values())
        for key in ["primary", "secondary"]
    )


def extract_array(value) -> list:
    if isinstance(value, list):
        return value
    if not isinstance(value, dict):
        return []
    for key in ["data", "items", "threads", "models", "skills", "servers", "rateLimits"]:
        child = value.get(key)
        if isinstance(child, list):
            return child
    return []


def read_string(record: dict, key: str) -> Optional[str]:
    value = record.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else None
