from typing import Dict, Optional

from .models import PROVIDER_ID


async def resolveFirstGithubToken(params: Dict) -> Dict:
    env = params.get("env") or {}
    envToken = env.get("COPILOT_GITHUB_TOKEN") or env.get("GH_TOKEN") or env.get("GITHUB_TOKEN") or ""
    githubToken = envToken.strip()
    hasProfile = False

    return {"githubToken": githubToken, "hasProfile": hasProfile}

__all__ = ["resolveFirstGithubToken"]