from typing import Dict

from .provider_models import DEEPINFRA_BASE_URL, DEEPINFRA_DEFAULT_MODEL_REF


def apply_deepinfra_config(cfg: Dict[str, any], model_ref: str = DEEPINFRA_DEFAULT_MODEL_REF) -> Dict[str, any]:
    models = cfg.get("agents", {}).get("defaults", {}).get("models", {}).copy()

    if model_ref not in models:
        models[model_ref] = {}
    models[model_ref]["alias"] = models[model_ref].get("alias", "DeepInfra")

    return {
        **cfg,
        "agents": {
            **cfg.get("agents", {}),
            "defaults": {
                **cfg.get("agents", {}).get("defaults", {}),
                "models": models,
                "model": model_ref,
            },
        },
    }

__all__ = ["DEEPINFRA_BASE_URL", "DEEPINFRA_DEFAULT_MODEL_REF", "apply_deepinfra_config"]