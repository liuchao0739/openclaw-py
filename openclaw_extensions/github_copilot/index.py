from typing import Dict, Optional

from .auth import resolveFirstGithubToken
from .embeddings import githubCopilotMemoryEmbeddingProviderAdapter
from .model_metadata import resolveCopilotExtendedThinkingLevels
from .models import PROVIDER_ID, fetchCopilotModelCatalog, resolveCopilotForwardCompatModel
from .replay_policy import buildGithubCopilotReplayPolicy, sanitizeGithubCopilotReplayHistory
from .stream import wrapCopilotProviderStream
from .token import DEFAULT_COPILOT_API_BASE_URL, resolveCopilotApiToken

COPILOT_ENV_VARS = ["COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"]
DEFAULT_COPILOT_MODEL = "github-copilot/claude-opus-4.7"
DEFAULT_COPILOT_PROFILE_ID = "github-copilot:github"


def applyCopilotDefaultModel(cfg: Dict) -> Dict:
    defaults = cfg.get("agents", {}).get("defaults", {})
    existingModel = defaults.get("model")
    existingPrimary = ""

    if isinstance(existingModel, str):
        existingPrimary = existingModel.strip()
    elif isinstance(existingModel, dict) and isinstance(existingModel.get("primary"), str):
        existingPrimary = existingModel["primary"].strip()

    if existingPrimary:
        return cfg

    fallbacks = existingModel.get("fallbacks") if isinstance(existingModel, dict) and existingModel else None

    return {
        **cfg,
        "agents": {
            **cfg.get("agents", {}),
            "defaults": {
                **defaults,
                "model": {
                    **({"fallbacks": fallbacks} if fallbacks else {}),
                    "primary": DEFAULT_COPILOT_MODEL,
                },
                "models": {
                    **defaults.get("models", {}),
                    DEFAULT_COPILOT_MODEL: defaults.get("models", {}).get(DEFAULT_COPILOT_MODEL, {}),
                },
            },
        },
    }


async def runGithubCopilotCatalog(ctx: Dict) -> Optional[Dict]:
    pluginConfig = ctx.get("config", {}).get("plugins", {}).get("github-copilot", {})
    discoveryEnabled = pluginConfig.get("discovery", {}).get("enabled")
    if discoveryEnabled is False:
        return None

    result = await resolveFirstGithubToken({
        "agentDir": ctx.get("agentDir"),
        "config": ctx.get("config"),
        "env": ctx.get("env", {}),
    })
    githubToken = result.get("githubToken")
    hasProfile = result.get("hasProfile")

    if not hasProfile and not githubToken:
        return None

    baseUrl = DEFAULT_COPILOT_API_BASE_URL
    copilotApiToken = None

    if githubToken:
        try:
            token = await resolveCopilotApiToken({"githubToken": githubToken, "env": ctx.get("env", {})})
            baseUrl = token.get("baseUrl", DEFAULT_COPILOT_API_BASE_URL)
            copilotApiToken = token.get("token")
        except Exception:
            baseUrl = DEFAULT_COPILOT_API_BASE_URL

    discoveredModels = []
    if copilotApiToken:
        try:
            discoveredModels = await fetchCopilotModelCatalog({
                "copilotApiToken": copilotApiToken,
                "baseUrl": baseUrl,
            })
        except Exception:
            discoveredModels = []

    return {
        "provider": {
            "baseUrl": baseUrl,
            "models": discoveredModels,
        },
    }


async def runGithubCopilotUnifiedLiveCatalog(ctx: Dict) -> Optional[list]:
    result = await runGithubCopilotCatalog(ctx)
    if not result or "provider" not in result:
        return None

    models = result.get("provider", {}).get("models", [])
    return [{
        "kind": "text",
        "provider": PROVIDER_ID,
        "model": model.get("id"),
        "source": "live",
        **({"label": model.get("name")} if model.get("name") else {}),
    } for model in models]


async def runGitHubCopilotAuth(ctx: Dict) -> Dict:
    await ctx.get("prompter", {}).get("note", lambda msg, title: None)(
        "This will open a GitHub device login to authorize Copilot.\nRequires an active GitHub Copilot subscription.",
        "GitHub Copilot",
    )

    from .login import runGitHubCopilotDeviceFlow

    async def show_code(data):
        await ctx.get("prompter", {}).get("note", lambda msg, title: None)(
            "\n".join([
                "Open this URL in your browser and enter the code below.",
                f"URL: {data.get('verificationUrl')}",
                f"Code: {data.get('userCode')}",
                f"Code expires in {max(1, round(data.get('expiresInMs', 900000) / 60000))} minutes. Never share it.",
                "",
                "If a browser does not open automatically after you continue, copy the URL manually.",
            ]),
            "Authorize GitHub Copilot",
        )

    async def open_url(url):
        await ctx.get("openUrl", lambda url: None)(url)

    result = await runGitHubCopilotDeviceFlow({
        "showCode": show_code,
        "openUrl": open_url,
    })

    if result.get("status") == "access_denied":
        await ctx.get("prompter", {}).get("note", lambda msg, title: None)("GitHub Copilot login was cancelled.", "GitHub Copilot")
        return {"profiles": []}

    if result.get("status") == "expired":
        await ctx.get("prompter", {}).get("note", lambda msg, title: None)(
            "The GitHub device code expired. Retry login to get a new code.",
            "GitHub Copilot",
        )
        return {"profiles": []}

    return {
        "profiles": [{
            "profileId": DEFAULT_COPILOT_PROFILE_ID,
            "credential": {
                "type": "token",
                "provider": PROVIDER_ID,
                "token": result.get("accessToken"),
            },
        }],
        "defaultModel": DEFAULT_COPILOT_MODEL,
    }


async def runGitHubCopilotNonInteractiveAuth(ctx: Dict) -> Optional[Dict]:
    opts = ctx.get("opts", {})
    flagValue = opts.get("githubCopilotToken")

    resolved = None
    if ctx.get("opts", {}).get("secretInputMode") == "ref":
        for envVar in COPILOT_ENV_VARS:
            resolved = ctx.get("env", {}).get(envVar)
            if resolved:
                break
        if not resolved and flagValue:
            ctx.get("runtime", {}).get("error", lambda msg: None)(
                "--github-copilot-token cannot be used with --secret-input-mode ref unless COPILOT_GITHUB_TOKEN, GH_TOKEN, or GITHUB_TOKEN is set in env.\n"
                "Set one of those env vars and omit --github-copilot-token, or use --secret-input-mode plaintext."
            )
            ctx.get("runtime", {}).get("exit", lambda code: None)(1)
            return None
    else:
        primary = flagValue or ctx.get("env", {}).get(COPILOT_ENV_VARS[0])
        if primary:
            resolved = primary
        else:
            for envVar in COPILOT_ENV_VARS[1:]:
                resolved = ctx.get("env", {}).get(envVar)
                if resolved:
                    break

    if resolved:
        pass
    else:
        ctx.get("runtime", {}).get("error", lambda msg: None)(
            "Missing --github-copilot-token (or COPILOT_GITHUB_TOKEN / GH_TOKEN / GITHUB_TOKEN env var) for --auth-choice github-copilot."
        )
        ctx.get("runtime", {}).get("exit", lambda code: None)(1)
        return None

    return applyCopilotDefaultModel(ctx.get("config", {}))


async def prepare_runtime_auth(ctx):
    token_result = await resolveCopilotApiToken({"githubToken": ctx.get("apiKey"), "env": ctx.get("env", {})})
    return {
        "apiKey": token_result.get("token"),
        "baseUrl": token_result.get("baseUrl"),
        "expiresAt": token_result.get("expiresAt"),
    }


def load_github_copilot_extension():
    return {
        "id": "github-copilot",
        "name": "GitHub Copilot Provider",
        "description": "Bundled GitHub Copilot provider plugin",
        "register": lambda api: {
            "memoryEmbeddingProviders": [githubCopilotMemoryEmbeddingProviderAdapter],
            "providers": [{
                "id": PROVIDER_ID,
                "label": "GitHub Copilot",
                "docsPath": "/providers/models",
                "envVars": COPILOT_ENV_VARS,
                "auth": [{
                    "id": "device",
                    "label": "GitHub device login",
                    "hint": "Browser device-code flow",
                    "kind": "device_code",
                    "run": runGitHubCopilotAuth,
                    "runNonInteractive": runGitHubCopilotNonInteractiveAuth,
                }],
                "wizard": {
                    "setup": {
                        "choiceId": "github-copilot",
                        "choiceLabel": "GitHub Copilot",
                        "choiceHint": "Device login with your GitHub account",
                        "methodId": "device",
                        "modelSelection": {
                            "promptWhenAuthChoiceProvided": True,
                        },
                    },
                },
                "catalog": {
                    "order": "late",
                    "run": runGithubCopilotCatalog,
                },
                "resolveDynamicModel": resolveCopilotForwardCompatModel,
                "wrapStreamFn": wrapCopilotProviderStream,
                "buildReplayPolicy": lambda params: buildGithubCopilotReplayPolicy(params.get("modelId")),
                "sanitizeReplayHistory": sanitizeGithubCopilotReplayHistory,
                "resolveThinkingProfile": lambda params: {
                    "levels": [
                        {"id": "off"},
                        {"id": "minimal"},
                        {"id": "low"},
                        {"id": "medium"},
                        {"id": "high"},
                        *[{"id": level} for level in resolveCopilotExtendedThinkingLevels(params.get("modelId"), params.get("compat"))],
                    ],
                },
                "prepareRuntimeAuth": prepare_runtime_auth,
            }],
            "modelCatalogProviders": [{
                "provider": PROVIDER_ID,
                "kinds": ["text"],
                "liveCatalog": runGithubCopilotUnifiedLiveCatalog,
            }],
        },
    }

__all__ = ["load_github_copilot_extension"]