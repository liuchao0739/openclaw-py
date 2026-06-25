"""Git source parsing helpers.

Normalizes git-style package references into clone URL, host/path, and optional
ref metadata. This is a simplified port without the hosted-git-info dependency;
it handles common GitHub/GitLab URL formats.
"""

from __future__ import annotations

import re
from typing import Any, TypedDict
from urllib.parse import urlparse


class GitSource(TypedDict, total=False):
    type: str
    repo: str
    host: str
    path: str
    ref: str | None
    pinned: bool


def _split_path_ref(
    original_repo: str,
    path_with_maybe_ref: str,
    build_repo: Any,
) -> dict[str, str | None]:
    ref_separator = path_with_maybe_ref.find("@")
    if ref_separator < 0:
        return {"repo": original_repo, "ref": None}
    repo_path = path_with_maybe_ref[:ref_separator]
    ref = path_with_maybe_ref[ref_separator + 1:]
    if not repo_path or not ref:
        return {"repo": original_repo, "ref": None}
    return {"repo": build_repo(repo_path), "ref": ref}


def _split_ref(url: str) -> dict[str, str | None]:
    scp_like_match = re.match(r"^git@([^:]+):(.+)$", url)
    if scp_like_match:
        return _split_path_ref(
            url,
            scp_like_match.group(2) or "",
            lambda repo_path: f"git@{scp_like_match.group(1)}:{repo_path}",
        )

    if "://" in url:
        try:
            parsed = urlparse(url)
            path = parsed.path.lstrip("/")
            return _split_path_ref(
                url,
                path,
                lambda repo_path: f"{parsed.scheme}://{parsed.netloc}/{repo_path}",
            )
        except Exception:
            return {"repo": url, "ref": None}

    slash_index = url.find("/")
    if slash_index < 0:
        return {"repo": url, "ref": None}
    host = url[:slash_index]
    return _split_path_ref(
        url,
        url[slash_index + 1:],
        lambda repo_path: f"{host}/{repo_path}",
    )


def _is_safe_git_host(host: str) -> bool:
    return bool(host) and "/" not in host and "\\" not in host and host != "." and host != ".."


def _normalize_git_path(path: str) -> str | None:
    normalized = re.sub(r"\.git$", "", path).lstrip("/")
    segments = normalized.split("/")
    if len(segments) < 2:
        return None
    for segment in segments:
        if not segment or segment == "." or segment == ".." or "\\" in segment:
            return None
    return "/".join(segments)


def _parse_generic_git_url(url: str) -> GitSource | None:
    split = _split_ref(url)
    repo = split["repo"] or ""
    ref = split.get("ref")
    host: str = ""
    path: str = ""

    scp_like_match = re.match(r"^git@([^:]+):(.+)$", repo)
    if scp_like_match:
        host = scp_like_match.group(1) or ""
        path = scp_like_match.group(2) or ""
    elif repo.startswith(("https://", "http://", "ssh://", "git://")):
        try:
            parsed = urlparse(repo)
            host = parsed.hostname or ""
            path = parsed.path.lstrip("/")
        except Exception:
            return None
    else:
        slash_index = repo.find("/")
        if slash_index < 0:
            return None
        host = repo[:slash_index]
        path = repo[slash_index + 1:]
        if "." not in host and host != "localhost":
            return None
        repo = f"https://{repo}"

    normalized_path = _normalize_git_path(path)
    if not _is_safe_git_host(host) or not normalized_path:
        return None

    return GitSource(
        type="git",
        repo=repo,
        host=host,
        path=normalized_path,
        ref=ref,
        pinned=bool(ref),
    )


def parse_git_url(source: str) -> GitSource | None:
    """Parse git source into a GitSource.

    Rules:
    - With git: prefix, accept all historical shorthand forms.
    - Without git: prefix, only accept explicit protocol URLs.
    """
    trimmed = source.strip()
    has_git_prefix = trimmed.startswith("git:")
    url = trimmed[4:].strip() if has_git_prefix else trimmed

    if not has_git_prefix and not re.match(r"^(https?|ssh|git)://", url, re.IGNORECASE):
        # Also accept SCP-like URLs (git@host:path)
        if not re.match(r"^git@", url):
            return None

    return _parse_generic_git_url(url)
