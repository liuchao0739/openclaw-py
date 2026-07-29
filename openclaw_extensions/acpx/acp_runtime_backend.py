from typing import Any, Optional


class AcpRuntimeError(Exception):
    def __init__(self, message: str, *, code: str = "acp_runtime_error", details: Optional[list] = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or []


AcpRuntimeErrorCode = str

_backends: dict = {}


def register_acp_runtime_backend(params: dict) -> None:
    backend_id = params.get("id")
    if not isinstance(backend_id, str) or not backend_id:
        raise ValueError("ACP runtime backend id is required")
    _backends[backend_id] = {
        "id": backend_id,
        "runtime": params.get("runtime"),
        "healthy": params.get("healthy"),
    }


def unregister_acp_runtime_backend(backend_id: str) -> None:
    _backends.pop(backend_id, None)


def get_acp_runtime_backend(backend_id: str) -> Optional[dict]:
    return _backends.get(backend_id)


async def try_dispatch_acp_reply_hook(event: Any, ctx: Any) -> dict:
    return {"handled": False}


def list_known_provider_auth_env_var_names() -> list:
    return []


def omit_env_keys_caseInsensitive(env: dict, names: list) -> dict:
    if not isinstance(env, dict):
        return {}
    lowered_names = {str(n).lower() for n in (names or [])}
    return {k: v for k, v in env.items() if str(k).lower() not in lowered_names}


def omit_env_keys_case_insensitive(env: dict, names: list) -> dict:
    return omit_env_keys_caseInsensitive(env, names)
