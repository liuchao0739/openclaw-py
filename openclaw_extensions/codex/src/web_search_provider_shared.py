from openclaw.plugin_sdk.provider_web_search_contract import create_web_search_provider_contract_fields


def create_codex_web_search_provider_base() -> dict:
    base = {
        "id": "codex",
        "label": "Codex Hosted Search",
        "hint": "Grounded answers through your Codex app-server account",
        "onboardingScopes": ["text-inference"],
        "requiresCredential": False,
        "envVars": [],
        "placeholder": "(uses Codex sign-in)",
        "signupUrl": "https://chatgpt.com/codex",
        "docsUrl": "https://docs.openclaw.ai/tools/web",
        "autoDetectOrder": 900,
        "credentialPath": "",
        **create_web_search_provider_contract_fields({
            "credentialPath": "",
            "searchCredential": {"type": "none"},
            "selectionPluginId": "codex",
        }),
    }

    async def _run_setup(ctx):
        await ctx["prompter"].note(
            "\n".join([
                "Codex Hosted Search uses the bundled Codex app-server and your Codex/OpenAI sign-in.",
                "If needed, sign in with: openclaw models auth login --provider openai",
                "Verify the app-server account with /codex status.",
            ]),
            "Codex Hosted Search",
        )
        return ctx["config"]

    base["runSetup"] = _run_setup
    return base
