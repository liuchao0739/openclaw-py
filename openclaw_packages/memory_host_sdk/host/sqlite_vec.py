from __future__ import annotations

from typing import Optional

from .error_utils import format_error_message
from .string_utils import normalize_optional_string


_SQLITE_VEC_CONFIG_HINT = (
    "Set agents.defaults.memorySearch.store.vector.extensionPath, or an agent-specific "
    "memorySearch.store.vector.extensionPath, to a sqlite-vec loadable extension path."
)


def resolve_sqlite_vec_platform_variant() -> Optional[dict]:
    import platform
    import sys

    machine = platform.machine().lower()
    system = platform.system().lower()

    variant_map = {
        ("x86_64", "linux"): {"pkg": "sqlite-vec-linux-x64", "extensionPath": "sqlite-vec"},
        ("x86_64", "darwin"): {"pkg": "sqlite-vec-darwin-x64", "extensionPath": "sqlite-vec"},
        ("arm64", "linux"): {"pkg": "sqlite-vec-linux-arm64", "extensionPath": "sqlite-vec"},
        ("arm64", "darwin"): {"pkg": "sqlite-vec-darwin-arm64", "extensionPath": "sqlite-vec"},
    }

    return variant_map.get((machine, system))


def _is_missing_sqlite_vec_package_error(err: object) -> bool:
    message = format_error_message(err)
    return "sqlite-vec" in message and "Cannot find" in message


def load_sqlite_vec_extension(
    db_path: str,
    extension_path: Optional[str] = None,
) -> dict:
    import sqlite3

    resolved_path = normalize_optional_string(extension_path)
    conn = sqlite3.connect(db_path)
    try:
        if resolved_path:
            conn.enable_load_extension(True)
            conn.load_extension(resolved_path)
            try:
                row = conn.execute("SELECT vec_version()").fetchone()
                if not row:
                    raise RuntimeError("vec_version() did not return a version")
            except Exception:
                raise RuntimeError(f"sqlite-vec health check failed after loading {resolved_path}")
            return {"ok": True, "extensionPath": resolved_path}

        try:
            conn.enable_load_extension(True)
            conn.load_extension("sqlite-vec")
            row = conn.execute("SELECT vec_version()").fetchone()
            if not row:
                raise RuntimeError("vec_version() did not return a version")
            return {"ok": True, "extensionPath": "sqlite-vec"}
        except Exception as err:
            variant = resolve_sqlite_vec_platform_variant()
            if not variant:
                if not _is_missing_sqlite_vec_package_error(err):
                    raise
                message = format_error_message(err)
                return {
                    "ok": False,
                    "error": f"sqlite-vec package is not installed. {_SQLITE_VEC_CONFIG_HINT} Original error: {message}",
                }
            try:
                conn.load_extension(variant["extensionPath"])
                row = conn.execute("SELECT vec_version()").fetchone()
                if not row:
                    raise RuntimeError("vec_version() did not return a version")
                return {"ok": True, "extensionPath": variant["extensionPath"]}
            except Exception as variant_err:
                message = format_error_message(variant_err)
                return {
                    "ok": False,
                    "error": f"sqlite-vec platform variant {variant['pkg']} failed. {_SQLITE_VEC_CONFIG_HINT} Error: {message}",
                }
    except Exception as err:
        return {"ok": False, "error": format_error_message(err)}
    finally:
        conn.close()
