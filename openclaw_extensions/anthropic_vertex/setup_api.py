from .region import resolve_anthropic_vertex_config_api_key


def build_setup_entry() -> dict:
    def _resolve_config_api_key(params):
        return resolve_anthropic_vertex_config_api_key(params.get("env"))

    return {
        "id": "anthropic-vertex",
        "name": "Anthropic Vertex Setup",
        "description": "Lightweight Anthropic Vertex setup hooks",
        "register": lambda api: api.register_provider({
            "id": "anthropic-vertex",
            "label": "Anthropic Vertex",
            "auth": [],
            "resolveConfigApiKey": _resolve_config_api_key,
        }),
    }


plugin_entry = build_setup_entry()
