"""Pure functional auth resolver for the copilot agent runtime.

Scope:

  - Consumes the resolved auth signals that core's harness contract
    already carries on ``EmbeddedRunAttemptParams`` (=
    ``AgentHarnessAttemptParams``): ``resolvedApiKey``, ``authProfileId``,
    ``authProfileIdSource``. Core resolves these from the agent's
    ``AuthProfileStore`` via ``provider-usage.auth.ts:resolveProviderAuths``
    before invoking the harness, so the harness does not re-perform
    the lookup (and could not, due to the package boundary in
    ``tsconfig.package-boundary.base.json``).
  - Reads optional explicit overrides from the harness attempt params
    (``auth.useLoggedInUser``, ``auth.gitHubToken``) for direct CLI / test
    use cases.
  - Falls back to OPENCLAW_GITHUB_TOKEN, COPILOT_GITHUB_TOKEN,
    GH_TOKEN, or GITHUB_TOKEN env vars (in that precedence) when
    no contract-resolved token is given; synthesises a stable,
    non-reversible pool fingerprint so token rotation busts the
    client pool cleanly.
  - Computes a per-agent ``copilotHome`` default
    (``<openClawHome>/.openclaw/agents/<agentId>/copilot``, or
    ``<agentDir>/copilot`` when an agent directory is supplied) that
    respects ``OPENCLAW_HOME`` for the home directory root.
  - Defaults to ``useLoggedInUser`` when no token signal is available.

Precedence (highest to lowest):
  1. ``auth.useLoggedInUser === true`` (explicit user opt-in)
  2. ``auth.gitHubToken`` (explicit override; requires
     ``profileId`` + ``profileVersion``)
  3. ``resolvedApiKey`` + ``authProfileId`` from the contract (core's
     AuthProfileStore-resolved token — the production main path for
     a configured ``github-copilot`` auth profile)
  4. OPENCLAW_GITHUB_TOKEN, then COPILOT_GITHUB_TOKEN, then
     GH_TOKEN, then GITHUB_TOKEN env vars (mirrors the
     shipped ``github-copilot`` provider precedence so headless
     users who already follow the documented
     COPILOT_GITHUB_TOKEN / GH_TOKEN setup get the token they
     configured rather than silently falling through to the
     logged-in CLI user.)
  5. ``useLoggedInUser`` (default)
"""

# ruff: noqa: BLE001, S110

from __future__ import annotations

import hashlib
import os
import re
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Literal, NotRequired, TypedDict

COPILOT_TOKEN_PROFILE_ERROR = (
    "[copilot-attempt] gitHubToken auth requires profileId+profileVersion "
    "(pool keying safety; per Q5/Q1 decisions)"
)

COPILOT_DEFAULT_AGENT_ID = "copilot"

_AuthMode = Literal["useLoggedInUser", "gitHubToken", "byok"]

_AGENT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


class ResolvedCopilotAuth(TypedDict):
    auth_mode: _AuthMode
    copilot_home: str
    agent_id: str
    git_hub_token: NotRequired[str]
    auth_profile_id: NotRequired[str]
    auth_profile_version: NotRequired[str]


class CopilotAuthOverride(TypedDict, total=False):
    git_hub_token: str
    use_logged_in_user: bool
    profile_id: str
    profile_version: str


class ResolveCopilotAuthInput(TypedDict, total=False):
    agent_id: str
    agent_dir: str
    workspace_dir: str
    copilot_home: str
    auth: CopilotAuthOverride
    resolved_api_key: str
    auth_profile_id: str
    profile_version: str
    env: Mapping[str, str | None]
    home_dir: Callable[[], str]


def create_copilot_byok_auth(
    *,
    agent_id: str | None = None,
    agent_dir: str | None = None,
    workspace_dir: str | None = None,
    copilot_home: str | None = None,
    auth_profile_id: str | None = None,
    auth_profile_version: str | None = None,
    env: Mapping[str, str | None] | None = None,
    home_dir: Callable[[], str] | None = None,
) -> ResolvedCopilotAuth:
    base = resolve_copilot_auth(
        {
            "agent_id": agent_id,
            "agent_dir": agent_dir,
            "workspace_dir": workspace_dir,
            "copilot_home": copilot_home,
            "env": env,
            "home_dir": home_dir,
            "auth": {"use_logged_in_user": True},
        }
    )
    trimmed_profile_id = (auth_profile_id or "").strip()
    trimmed_profile_version = (auth_profile_version or "").strip()
    return {
        **base,
        "auth_mode": "byok",
        "auth_profile_id": trimmed_profile_id or "byok:resolved",
        "auth_profile_version": trimmed_profile_version or "byok:unfingerprinted",
    }


def resolve_copilot_auth(input: ResolveCopilotAuthInput | None = None, /, **kwargs: object) -> ResolvedCopilotAuth:
    params: dict[str, object] = dict(input or {})
    params.update(kwargs)

    env: Mapping[str, str | None] = (
        params["env"] if "env" in params and params["env"] is not None else os.environ
    )
    home_dir_fn: Callable[[], str] = (
        params["home_dir"] if callable(params.get("home_dir")) else (lambda: str(Path.home()))
    )

    agent_id = sanitize_agent_id(params.get("agent_id"))  # type: ignore[arg-type]
    copilot_home = _resolve_copilot_home(
        explicit=_read_string(params.get("copilot_home")),
        agent_dir=_read_string(params.get("agent_dir")),
        workspace_dir=_read_string(params.get("workspace_dir")),
        agent_id=agent_id,
        env=env,
        home_dir=home_dir_fn,
    )

    auth = params.get("auth")
    auth_dict = auth if isinstance(auth, dict) else {}

    explicit_token = _read_string(auth_dict.get("git_hub_token"))
    explicit_profile_id = _read_string(auth_dict.get("profile_id")) or _read_string(
        params.get("auth_profile_id")
    )
    explicit_profile_version = _read_string(auth_dict.get("profile_version")) or _read_string(
        params.get("profile_version")
    )

    if auth_dict.get("use_logged_in_user") is True:
        return {
            "auth_mode": "useLoggedInUser",
            "copilot_home": copilot_home,
            "agent_id": agent_id,
        }

    if explicit_token:
        if not explicit_profile_id or not explicit_profile_version:
            raise ValueError(COPILOT_TOKEN_PROFILE_ERROR)
        return {
            "auth_mode": "gitHubToken",
            "git_hub_token": explicit_token,
            "auth_profile_id": explicit_profile_id,
            "auth_profile_version": explicit_profile_version,
            "copilot_home": copilot_home,
            "agent_id": agent_id,
        }

    contract_token = _read_string(params.get("resolved_api_key"))
    if contract_token:
        contract_profile_id = _read_string(params.get("auth_profile_id"))
        return {
            "auth_mode": "gitHubToken",
            "git_hub_token": contract_token,
            "auth_profile_id": contract_profile_id or "pi:resolved",
            "auth_profile_version": token_fingerprint(contract_token),
            "copilot_home": copilot_home,
            "agent_id": agent_id,
        }

    env_fallback = _read_env_token_fallback(env)
    if env_fallback:
        return {
            "auth_mode": "gitHubToken",
            "git_hub_token": env_fallback["token"],
            "auth_profile_id": env_fallback["profile_id"],
            "auth_profile_version": env_fallback["profile_version"],
            "copilot_home": copilot_home,
            "agent_id": agent_id,
        }

    return {
        "auth_mode": "useLoggedInUser",
        "copilot_home": copilot_home,
        "agent_id": agent_id,
    }


def sanitize_agent_id(value: str | None) -> str:
    trimmed = (value or "").strip().lower()
    if not trimmed:
        return COPILOT_DEFAULT_AGENT_ID
    if not _AGENT_ID_RE.fullmatch(trimmed):
        return COPILOT_DEFAULT_AGENT_ID
    return trimmed


def token_fingerprint(token: str) -> str:
    hex_digest = hashlib.sha256(token.encode()).hexdigest()[:12]
    return f"sha256:{hex_digest}"


def _resolve_copilot_home(
    *,
    explicit: str | None,
    agent_dir: str | None,
    workspace_dir: str | None,
    agent_id: str,
    env: Mapping[str, str | None],
    home_dir: Callable[[], str],
) -> str:
    del workspace_dir  # mirrored from TS signature; unused in resolution logic

    if explicit:
        return str(Path(explicit).resolve())

    if agent_dir:
        return str(Path(agent_dir).joinpath("copilot").resolve())

    openclaw_home = _read_string(env.get("OPENCLAW_HOME"))
    root_home = str(Path(openclaw_home).resolve()) if openclaw_home else _safe_home_dir(home_dir)
    return str(
        Path(root_home)
        .joinpath(".openclaw", "agents", agent_id, "copilot")
        .resolve()
    )


def _safe_home_dir(home_dir: Callable[[], str]) -> str:
    try:
        value = home_dir()
        if isinstance(value, str) and len(value) > 0:
            return value
    except Exception:
        pass
    return os.getcwd()


def _read_env_token_fallback(
    env: Mapping[str, str | None],
) -> dict[str, str] | None:
    candidates: list[tuple[str, str | None]] = [
        ("OPENCLAW_GITHUB_TOKEN", _read_string(env.get("OPENCLAW_GITHUB_TOKEN"))),
        ("COPILOT_GITHUB_TOKEN", _read_string(env.get("COPILOT_GITHUB_TOKEN"))),
        ("GH_TOKEN", _read_string(env.get("GH_TOKEN"))),
        ("GITHUB_TOKEN", _read_string(env.get("GITHUB_TOKEN"))),
    ]
    for name, value in candidates:
        if value:
            return {
                "token": value,
                "profile_id": f"env:{name}",
                "profile_version": token_fingerprint(value),
            }
    return None


def _read_string(value: object) -> str | None:
    return value if isinstance(value, str) and len(value) > 0 else None
