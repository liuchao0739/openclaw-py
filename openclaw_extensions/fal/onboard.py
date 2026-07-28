from typing import Dict


DEFAULT_FAL_MODEL_REF = "fal-ai/flux/dev"


def apply_fal_config(cfg: Dict, model_ref: str = DEFAULT_FAL_MODEL_REF) -> Dict:
    models = cfg.get("agents", {}).get("defaults", {}).get("models", {}).copy()
    
    if model_ref not in models:
        models[model_ref] = {}
    models[model_ref]["alias"] = models[model_ref].get("alias", "fal")
    
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