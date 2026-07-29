from .acp_runtime_backend import try_dispatch_acp_reply_hook
from .service import create_acpx_runtime_service


def _register(api) -> None:
    plugin_config = api.get("pluginConfig") if isinstance(api, dict) else getattr(api, "plugin_config", None)
    open_keyed_store = None
    runtime = api.get("runtime") if isinstance(api, dict) else getattr(api, "runtime", None)
    if isinstance(runtime, dict):
        state = runtime.get("state")
        if isinstance(state, dict):
            open_keyed_store = state.get("openKeyedStore")
    elif runtime is not None:
        state = getattr(runtime, "state", None)
        if state is not None:
            open_keyed_store = getattr(state, "open_keyed_store", None) or getattr(state, "openKeyedStore", None)

    service = create_acpx_runtime_service({
        "pluginConfig": plugin_config,
        "openKeyedStore": open_keyed_store,
    })

    register_service = api.get("registerService") if isinstance(api, dict) else getattr(api, "register_service", None) or getattr(api, "registerService", None)
    if callable(register_service):
        register_service(service)

    on_fn = api.get("on") if isinstance(api, dict) else getattr(api, "on", None)
    if callable(on_fn):
        on_fn("reply_dispatch", try_dispatch_acp_reply_hook)


plugin_entry: dict = {
    "id": "acpx",
    "name": "ACPX Runtime",
    "description": "Embedded ACP runtime backend with plugin-owned session and transport management.",
    "register": _register,
}
