def _normalize_lowercase_string_or_empty(value) -> str:
    if isinstance(value, str):
        return value.lower()
    return ""


def _register(api) -> None:
    register_fn = api.get("registerAutoEnableProbe") if isinstance(api, dict) else getattr(api, "register_auto_enable_probe", None) or getattr(api, "registerAutoEnableProbe", None)
    if not callable(register_fn):
        return
    register_fn(_auto_enable_probe)


def _auto_enable_probe(params) -> str:
    config = params.get("config", {}) if isinstance(params, dict) else getattr(params, "config", {})
    if not isinstance(config, dict):
        return None
    acp_config = config.get("acp")
    if not isinstance(acp_config, dict):
        return None
    backend_raw = _normalize_lowercase_string_or_empty(acp_config.get("backend"))
    dispatch_config = acp_config.get("dispatch")
    dispatch_enabled = isinstance(dispatch_config, dict) and dispatch_config.get("enabled") is True
    configured = (
        acp_config.get("enabled") is True
        or dispatch_enabled
        or backend_raw == "acpx"
    )
    if configured and (not backend_raw or backend_raw == "acpx"):
        return "ACP runtime configured"
    return None


plugin_entry: dict = {
    "id": "acpx",
    "name": "ACPX Setup",
    "description": "Lightweight ACPX setup hooks",
    "register": _register,
}
