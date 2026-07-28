from __future__ import annotations

import os
from pathlib import Path
from typing import Any


BLOCKED_PROVIDER_AUTH_WORKSPACE_DOTENV_KEYS: tuple[str, ...] = (
    "AI_GATEWAY_API_KEY",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_OAUTH_TOKEN",
    "ARCEEAI_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "AZURE_SPEECH_API_KEY",
    "AZURE_SPEECH_KEY",
    "AZURE_SPEECH_REGION",
    "BRAVE_API_KEY",
    "BYTEPLUS_API_KEY",
    "BYTEPLUS_SEED_SPEECH_API_KEY",
    "CEREBRAS_API_KEY",
    "CHUTES_API_KEY",
    "CHUTES_OAUTH_TOKEN",
    "CLOUDFLARE_AI_GATEWAY_API_KEY",
    "COMFY_API_KEY",
    "COMFY_CLOUD_API_KEY",
    "COPILOT_GITHUB_TOKEN",
    "DASHSCOPE_API_KEY",
    "DEEPGRAM_API_KEY",
    "DEEPINFRA_API_KEY",
    "DEEPSEEK_API_KEY",
    "ELEVENLABS_API_KEY",
    "EXA_API_KEY",
    "FAL_API_KEY",
    "FAL_KEY",
    "FIRECRAWL_API_KEY",
    "FIREWORKS_API_KEY",
    "GEMINI_API_KEY",
    "GH_TOKEN",
    "GITHUB_TOKEN",
    "GOOGLE_API_KEY",
    "GOOGLE_CLOUD_API_KEY",
    "GRADIUM_API_KEY",
    "GROQ_API_KEY",
    "HF_TOKEN",
    "HUGGINGFACE_HUB_TOKEN",
    "INWORLD_API_KEY",
    "KILOCODE_API_KEY",
    "KIMICODE_API_KEY",
    "KIMI_API_KEY",
    "LITELLM_API_KEY",
    "LM_API_TOKEN",
    "MINIMAX_API_KEY",
    "MINIMAX_CODE_PLAN_KEY",
    "MINIMAX_CODING_API_KEY",
    "MINIMAX_OAUTH_TOKEN",
    "MISTRAL_API_KEY",
    "MODELSTUDIO_API_KEY",
    "MOONSHOT_API_KEY",
    "NVIDIA_API_KEY",
    "OLLAMA_API_KEY",
    "OPENAI_API_KEY",
    "OPENCODE_API_KEY",
    "OPENCODE_ZEN_API_KEY",
    "OPENROUTER_API_KEY",
    "PERPLEXITY_API_KEY",
    "QIANFAN_API_KEY",
    "QWEN_API_KEY",
    "RUNWAY_API_KEY",
    "RUNWAYML_API_SECRET",
    "SENSEAUDIO_API_KEY",
    "SGLANG_API_KEY",
    "SPEECH_KEY",
    "SPEECH_REGION",
    "STEPFUN_API_KEY",
    "SYNTHETIC_API_KEY",
    "TAVILY_API_KEY",
    "TOGETHER_API_KEY",
    "TOKENHUB_API_KEY",
    "VENICE_API_KEY",
    "VLLM_API_KEY",
    "VOLCANO_ENGINE_API_KEY",
    "VOLCENGINE_TTS_API_KEY",
    "VOLCENGINE_TTS_APPID",
    "VOLCENGINE_TTS_TOKEN",
    "VOYAGE_API_KEY",
    "VYDRA_API_KEY",
    "XAI_API_KEY",
    "XIAOMI_API_KEY",
    "XI_API_KEY",
    "ZAI_API_KEY",
    "Z_AI_API_KEY",
)

BLOCKED_WORKSPACE_DOTENV_KEYS: set[str] = set([
    *BLOCKED_PROVIDER_AUTH_WORKSPACE_DOTENV_KEYS,
    "ALL_PROXY",
    "BROWSER_EXECUTABLE_PATH",
    "CLAWHUB_AUTH_TOKEN",
    "CLAWHUB_CONFIG_PATH",
    "CLAWHUB_TOKEN",
    "CLAWHUB_URL",
    "CLOUDSDK_PYTHON",
    "COMSPEC",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "HOMEBREW_BREW_FILE",
    "HOMEBREW_PREFIX",
    "IRC_HOST",
    "LOCALAPPDATA",
    "MATTERMOST_URL",
    "MATRIX_HOMESERVER",
    "MINIMAX_API_HOST",
    "NODE_TLS_REJECT_UNAUTHORIZED",
    "NO_PROXY",
    "NPM_EXECPATH",
    "OPENAI_API_KEYS",
    "OPENCLAW_AGENT_DIR",
    "OPENCLAW_ALLOW_PLUGIN_INSTALL_OVERRIDES",
    "OPENCLAW_ALLOW_INSECURE_PRIVATE_WS",
    "OPENCLAW_ALLOW_PROJECT_LOCAL_BIN",
    "OPENCLAW_BROWSER_EXECUTABLE_PATH",
    "OPENCLAW_BROWSER_CONTROL_MODULE",
    "OPENCLAW_BUNDLED_HOOKS_DIR",
    "OPENCLAW_BUNDLED_PLUGINS_DIR",
    "OPENCLAW_BUNDLED_SKILLS_DIR",
    "OPENCLAW_CACHE_TRACE",
    "OPENCLAW_CACHE_TRACE_FILE",
    "OPENCLAW_CACHE_TRACE_MESSAGES",
    "OPENCLAW_CACHE_TRACE_PROMPT",
    "OPENCLAW_CACHE_TRACE_SYSTEM",
    "OPENCLAW_CONFIG_PATH",
    "OPENCLAW_GATEWAY_PASSWORD",
    "OPENCLAW_GATEWAY_PORT",
    "OPENCLAW_GATEWAY_SECRET",
    "OPENCLAW_GATEWAY_TOKEN",
    "OPENCLAW_GATEWAY_URL",
    "OPENCLAW_HOME",
    "OPENCLAW_LIVE_ANTHROPIC_KEY",
    "OPENCLAW_LIVE_ANTHROPIC_KEYS",
    "OPENCLAW_LIVE_GEMINI_KEY",
    "OPENCLAW_LIVE_OPENAI_KEY",
    "OPENCLAW_MPM_CATALOG_PATHS",
    "OPENCLAW_NODE_EXEC_FALLBACK",
    "OPENCLAW_NODE_EXEC_HOST",
    "OPENCLAW_OAUTH_DIR",
    "OPENCLAW_PINNED_PYTHON",
    "OPENCLAW_PINNED_WRITE_PYTHON",
    "OPENCLAW_PLUGIN_INSTALL_OVERRIDES",
    "OPENCLAW_PLUGIN_CATALOG_PATHS",
    "OPENCLAW_PROFILE",
    "OPENCLAW_RAW_STREAM",
    "OPENCLAW_RAW_STREAM_PATH",
    "OPENCLAW_SHOW_SECRETS",
    "OPENCLAW_SKIP_BROWSER_CONTROL_SERVER",
    "OPENCLAW_STATE_DIR",
    "OPENCLAW_TEST_TAILSCALE_BINARY",
    "PATH",
    "PI_CODING_AGENT_DIR",
    "PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH",
    "PROGRAMFILES",
    "PROGRAMFILES(X86)",
    "PROGRAMW6432",
    "STATE_DIRECTORY",
    "SYNOLOGY_CHAT_INCOMING_URL",
    "SYNOLOGY_NAS_HOST",
    "UV_PYTHON",
])

BLOCKED_WORKSPACE_DOTENV_SUFFIXES: tuple[str, ...] = ("_API_HOST", "_BASE_URL", "_HOMESERVER")
BLOCKED_WORKSPACE_DOTENV_PREFIXES: tuple[str, ...] = (
    "ANTHROPIC_API_KEY_",
    "CLAWHUB_",
    "OPENAI_API_KEY_",
    "OPENCLAW_",
    "OPENCLAW_CLAWHUB_",
    "OPENCLAW_DISABLE_",
    "OPENCLAW_SKIP_",
    "OPENCLAW_UPDATE_",
)


def should_block_workspace_runtime_dotenv_key(key: str) -> bool:
    upper = key.upper()
    if upper in BLOCKED_WORKSPACE_DOTENV_KEYS:
        return True
    for prefix in BLOCKED_WORKSPACE_DOTENV_PREFIXES:
        if upper.startswith(prefix):
            return True
    for suffix in BLOCKED_WORKSPACE_DOTENV_SUFFIXES:
        if upper.endswith(suffix):
            return True
    return False


def read_dotenv_file(
    file_path: str,
    entry_filter: Any = None,
    quiet: bool = True,
) -> dict[str, Any] | None:
    path_obj = Path(file_path)
    if not path_obj.exists():
        return None
    try:
        content = path_obj.read_text(encoding="utf-8")
    except OSError:
        return None
    entries: list[dict[str, str]] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[7:]
        if "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip()
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1]
        if entry_filter and not entry_filter(key):
            continue
        entries.append({"key": key, "value": value})
    return {"entries": entries}


def load_workspace_dotenv_file(
    file_path: str,
    opts: dict[str, Any] | None = None,
) -> None:
    opts = opts or {}
    parsed = read_dotenv_file(
        file_path,
        entry_filter=lambda key: not should_block_workspace_runtime_dotenv_key(key),
        quiet=opts.get("quiet", True),
    )
    if not parsed:
        return
    for entry in parsed["entries"]:
        key = entry["key"]
        value = entry["value"]
        if key in os.environ:
            continue
        os.environ[key] = value


def load_global_runtime_dotenv_files(
    opts: dict[str, Any] | None = None,
) -> None:
    opts = opts or {}
    from openclaw.config.paths import resolve_state_dir
    state_dir = resolve_state_dir()
    env_path = str(Path(state_dir) / ".env")
    if Path(env_path).exists():
        load_workspace_dotenv_file(env_path, opts)


def load_dotenv(opts: dict[str, Any] | None = None) -> None:
    opts = opts or {}
    quiet = opts.get("quiet", True)
    cwd_env_path = str(Path.cwd() / ".env")
    load_workspace_dotenv_file(cwd_env_path, {"quiet": quiet})
    load_global_runtime_dotenv_files({"quiet": quiet})
