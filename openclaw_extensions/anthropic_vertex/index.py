from openclaw.plugin_sdk.plugin_entry import define_plugin_entry
from openclaw.plugin_sdk.provider_catalog_shared import read_configured_provider_catalog_entries
from openclaw.plugin_sdk.provider_model_shared import (
    NATIVE_ANTHROPIC_REPLAY_HOOKS,
    resolve_claude_thinking_profile,
)

from .api import (
    has_anthropic_vertex_available_auth,
    merge_implicit_anthropic_vertex_provider,
    resolve_anthropic_vertex_config_api_key,
    resolve_implicit_anthropic_vertex_provider,
)
from .provider_catalog import normalize_anthropic_vertex_resolved_model

PROVIDER_ID = "anthropic-vertex"
GCP_VERTEX_CREDENTIALS_MARKER = "gcp-vertex-credentials"


def _build_entry():
    def _register(api):
        def _catalog_run(ctx):
            implicit = resolve_implicit_anthropic_vertex_provider({"env": ctx.get("env")})
            if not implicit:
                return None
            config = ctx.get("config") or {}
            models = config.get("models") if isinstance(config, dict) else None
            providers = models.get("providers") if isinstance(models, dict) else None
            existing = providers.get(PROVIDER_ID) if isinstance(providers, dict) else None
            return {
                "provider": merge_implicit_anthropic_vertex_provider({
                    "existing": existing,
                    "implicit": implicit,
                })
            }

        def _resolve_config_api_key(params):
            return resolve_anthropic_vertex_config_api_key(params.get("env"))

        def _normalize_resolved_model(params):
            return normalize_anthropic_vertex_resolved_model(params["modelId"], params["model"])

        def _resolve_thinking_profile(params):
            return resolve_claude_thinking_profile(
                params["modelId"],
                params.get("params"),
                {"includeNativeMax": True},
            )

        def _resolve_synthetic_auth():
            if not has_anthropic_vertex_available_auth():
                return None
            return {
                "apiKey": GCP_VERTEX_CREDENTIALS_MARKER,
                "source": "gcp-vertex-credentials (ADC)",
                "mode": "api-key",
            }

        def _augment_model_catalog(params):
            return read_configured_provider_catalog_entries({
                "config": params["config"],
                "providerId": PROVIDER_ID,
            })

        provider = {
            "id": PROVIDER_ID,
            "label": "Anthropic Vertex",
            "docsPath": "/providers/models",
            "auth": [],
            "catalog": {"order": "simple", "run": _catalog_run},
            "resolveConfigApiKey": _resolve_config_api_key,
            **NATIVE_ANTHROPIC_REPLAY_HOOKS,
            "normalizeResolvedModel": _normalize_resolved_model,
            "resolveThinkingProfile": _resolve_thinking_profile,
            "resolveSyntheticAuth": _resolve_synthetic_auth,
            "augmentModelCatalog": _augment_model_catalog,
        }
        api.register_provider(provider)

    return define_plugin_entry({
        "id": PROVIDER_ID,
        "name": "Anthropic Vertex Provider",
        "description": "Bundled Anthropic Vertex provider plugin",
        "register": _register,
    })


plugin_entry = _build_entry()
