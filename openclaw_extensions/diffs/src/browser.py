from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .viewer_assets import (
    LANGUAGE_PACK_VIEWER_ASSET_PREFIX,
    VIEWER_ASSET_PREFIX,
    get_served_language_pack_viewer_asset,
    get_served_viewer_asset,
)

DEFAULT_BROWSER_IDLE_MS = 30_000
SHARED_BROWSER_KEY = "__default__"
IMAGE_SIZE_LIMIT_ERROR = "Diff frame did not render within image size limits."
PDF_REFERENCE_PAGE_HEIGHT_PX = 1056
MAX_PDF_PAGES = 50
LOCAL_VIEWER_BASE_HREF = "http://127.0.0.1/plugins/diffs/view/local/local"

_shared_browser_state: dict[str, Any] | None = None
_executable_path_cache: dict[str, Any] | None = None


def _inject_base_href(html: str) -> str:
    if "<base " in html:
        return html
    return html.replace("<head>", f'<head><base href="{LOCAL_VIEWER_BASE_HREF}" />')


async def _resolve_browser_executable_path(config: dict[str, Any]) -> str | None:
    global _executable_path_cache
    config_path = ((config or {}).get("browser") or {}).get("executablePath", "")
    cache_key = str({
        "configPath": (config_path or "").strip(),
        "env": [
            os.environ.get("OPENCLAW_BROWSER_EXECUTABLE_PATH", ""),
            os.environ.get("BROWSER_EXECUTABLE_PATH", ""),
            os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", ""),
        ],
        "path": os.environ.get("PATH", ""),
    })
    if _executable_path_cache and _executable_path_cache.get("key") == cache_key:
        return _executable_path_cache.get("value")
    value = await _resolve_browser_executable_path_uncached(config)
    _executable_path_cache = {"key": cache_key, "value": value}
    return value


async def _resolve_browser_executable_path_uncached(config: dict[str, Any]) -> str | None:
    config = config or {}
    browser_config = config.get("browser") or {}
    config_path = (browser_config.get("executablePath") or "").strip()
    if config_path:
        if await _is_executable(config_path):
            return config_path
        raise ValueError(f"browser.executablePath not found or not executable: {config_path}")
    env_candidates = [
        os.environ.get("OPENCLAW_BROWSER_EXECUTABLE_PATH"),
        os.environ.get("BROWSER_EXECUTABLE_PATH"),
        os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"),
    ]
    for candidate in env_candidates:
        if candidate and (await _is_executable(candidate.strip())):
            return candidate
    for candidate in _collect_executable_candidates():
        if await _is_executable(candidate):
            return candidate
    return None


async def _is_executable(candidate: str) -> bool:
    try:
        path = Path(candidate)
        return path.is_file() and os.access(str(path), os.X_OK)
    except Exception:
        return False


def _path_commands_for_platform() -> list[str]:
    if os.name == "nt":
        return ["chrome.exe", "msedge.exe", "brave.exe"]
    if os.uname().sysname == "Darwin":
        return ["google-chrome", "chromium", "msedge", "brave-browser", "brave"]
    return [
        "chromium",
        "chromium-browser",
        "google-chrome",
        "google-chrome-stable",
        "msedge",
        "brave-browser",
        "brave",
    ]


def _common_executable_paths_for_platform() -> list[str]:
    if os.uname().sysname == "Darwin":
        return [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        ]
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        return [
            str(Path(local_app_data) / "Google" / "Chrome" / "Application" / "chrome.exe"),
            str(Path(program_files) / "Google" / "Chrome" / "Application" / "chrome.exe"),
            str(Path(program_files_x86) / "Google" / "Chrome" / "Application" / "chrome.exe"),
            str(Path(program_files) / "Microsoft" / "Edge" / "Application" / "msedge.exe"),
            str(Path(program_files_x86) / "Microsoft" / "Edge" / "Application" / "msedge.exe"),
            str(Path(program_files) / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe"),
            str(Path(program_files_x86) / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe"),
        ]
    return [
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/msedge",
        "/usr/bin/brave-browser",
        "/snap/bin/chromium",
    ]


async def _collect_executable_candidates() -> list[str]:
    candidates: set[str] = set()
    for command in _path_commands_for_platform():
        resolved = shutil.which(command)
        if resolved:
            candidates.add(resolved)
    for candidate in _common_executable_paths_for_platform():
        candidates.add(candidate)
    return list(candidates)


async def _acquire_shared_browser(config: dict[str, Any], idle_ms: int) -> dict[str, Any]:
    global _shared_browser_state
    executable_path = await _resolve_browser_executable_path(config)
    desired_key = executable_path or SHARED_BROWSER_KEY
    if _shared_browser_state and _shared_browser_state.get("key") != desired_key:
        await _close_shared_browser()
    if not _shared_browser_state:
        browser = await _launch_browser(executable_path)
        _shared_browser_state = {
            "browser": browser,
            "idleTimer": None,
            "key": desired_key,
            "users": 0,
        }
    _shared_browser_state["users"] = _shared_browser_state.get("users", 0) + 1
    state = _shared_browser_state

    released = {"value": False}

    async def release() -> None:
        if released["value"]:
            return
        released["value"] = True
        state["users"] = max(0, state.get("users", 0) - 1)
        if state["users"] == 0:
            _schedule_idle_browser_close(state, idle_ms)

    return {"browser": state["browser"], "release": release}


def _schedule_idle_browser_close(state: dict[str, Any], idle_ms: int) -> None:
    global _shared_browser_state
    if state.get("idleTimer"):
        try:
            state["idleTimer"].cancel()
        except Exception:
            pass
    import asyncio

    async def _close_later() -> None:
        global _shared_browser_state
        if _shared_browser_state is state and state.get("users", 0) == 0:
            await _close_shared_browser()

    state["idleTimer"] = asyncio.ensure_future(_sleep_and_close(idle_ms / 1000.0, _close_later))


async def _sleep_and_close(seconds: float, callback: Any) -> None:
    import asyncio
    await asyncio.sleep(seconds)
    await callback()


async def _launch_browser(executable_path: str | None) -> Any:
    try:
        from playwright.sync_api import sync_playwright
        p = sync_playwright().start()
        launch_kwargs: dict[str, Any] = {"headless": True}
        if executable_path:
            launch_kwargs["executable_path"] = executable_path
        launch_kwargs["args"] = ["--disable-dev-shm-usage"]
        browser = p.chromium.launch(**launch_kwargs)
        return {"playwright": p, "browser": browser}
    except ImportError:
        return {"playwright": None, "browser": None}


async def _close_shared_browser() -> None:
    global _shared_browser_state
    if not _shared_browser_state:
        return
    state = _shared_browser_state
    _shared_browser_state = None
    if state.get("idleTimer"):
        try:
            state["idleTimer"].cancel()
        except Exception:
            pass
    browser_wrapper = state.get("browser")
    if browser_wrapper:
        try:
            browser = browser_wrapper.get("browser")
            if browser:
                browser.close()
        except Exception:
            pass
    playwright = browser_wrapper.get("playwright") if browser_wrapper else None
    if playwright:
        try:
            playwright.stop()
        except Exception:
            pass


async def reset_shared_browser_state_for_tests() -> None:
    global _executable_path_cache
    _executable_path_cache = None
    await _close_shared_browser()


class PlaywrightDiffScreenshotter:
    def __init__(self, config: dict[str, Any] | None = None, browser_idle_ms: int | None = None):
        self._config = config or {}
        self._browser_idle_ms = browser_idle_ms or DEFAULT_BROWSER_IDLE_MS

    async def screenshot_html(
        self,
        html: str,
        output_path: str,
        theme: str,
        image: dict[str, Any],
    ) -> str:
        html = _inject_base_href(html)
        lease = await _acquire_shared_browser(self._config, self._browser_idle_ms)
        try:
            from playwright.sync_api import sync_playwright
            p = sync_playwright().start()
            browser = p.chromium.launch(headless=True, args=["--disable-dev-shm-usage"])
            page = browser.new_page(
                viewport={
                    "width": max(int(image.get("maxWidth", 960)) + 240, 1200),
                    "height": 900,
                },
                device_scale_factor=image.get("scale", 2),
            )
            await page.set_content(html, wait_until="load")
            await page.wait_for_function(
                "() => document.documentElement.dataset.openclawDiffsReady === 'true'",
                timeout=10000,
            )
            import asyncio
            await asyncio.sleep(0.5)
            frame = page.locator(".oc-frame")
            await frame.wait_for()
            box = await frame.bounding_box()
            if not box:
                raise ValueError("Diff frame did not render.")
            is_pdf = image.get("format") == "pdf"
            padding = 0 if is_pdf else 20
            clip_width = max(int(box["width"]) + padding * 2, 1)
            clip_height = max(int(box["height"]) + padding * 2, 320)
            await page.set_viewport_size({
                "width": max(clip_width + padding, 900),
                "height": max(clip_height + padding, 700),
            })
            page_box = await frame.bounding_box()
            if not page_box:
                raise ValueError("Diff frame was lost after resizing.")
            if is_pdf:
                await page.emulate_media(media="screen")
                await page.evaluate("""() => {
                    const html = document.documentElement;
                    const body = document.body;
                    const frameLocal = document.querySelector('.oc-frame');
                    html.style.background = 'transparent';
                    body.style.margin = '0';
                    body.style.padding = '0';
                    body.style.background = 'transparent';
                    body.style.setProperty('-webkit-print-color-adjust', 'exact');
                    if (frameLocal) { frameLocal.style.margin = '0'; }
                }""")
                pdf_box = await frame.bounding_box()
                if not pdf_box:
                    raise ValueError("Diff frame was lost before PDF render.")
                pdf_width = max(int(pdf_box["width"]), 1)
                pdf_height = max(int(pdf_box["height"]), 1)
                estimated_pixels = pdf_width * pdf_height
                estimated_pages = max(1, int(pdf_height / PDF_REFERENCE_PAGE_HEIGHT_PX))
                max_pixels = image.get("maxPixels", 8000000)
                if estimated_pixels > max_pixels or estimated_pages > MAX_PDF_PAGES:
                    raise ValueError(IMAGE_SIZE_LIMIT_ERROR)
                output_dir = Path(output_path).parent
                output_dir.mkdir(parents=True, exist_ok=True)
                page.pdf(
                    path=output_path,
                    width=f"{pdf_width}px",
                    height=f"{pdf_height}px",
                    print_background=True,
                    margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                )
            else:
                dpr = page.evaluate("() => window.devicePixelRatio || 1")
                raw_x = max(page_box["x"] - padding, 0)
                raw_y = max(page_box["y"] - padding, 0)
                raw_right = raw_x + clip_width
                raw_bottom = raw_y + clip_height
                x = int(raw_x * dpr) / dpr
                y = int(raw_y * dpr) / dpr
                right = int(raw_right * dpr) / dpr
                bottom = int(raw_bottom * dpr) / dpr
                css_width = max(right - x, 1)
                css_height = max(bottom - y, 1)
                estimated_pixels = css_width * css_height * dpr * dpr
                max_pixels = image.get("maxPixels", 8000000)
                if estimated_pixels > max_pixels:
                    raise ValueError(IMAGE_SIZE_LIMIT_ERROR)
                output_dir = Path(output_path).parent
                output_dir.mkdir(parents=True, exist_ok=True)
                page.screenshot(
                    path=output_path,
                    type="png",
                    scale="device",
                    clip={"x": x, "y": y, "width": css_width, "height": css_height},
                )
            await page.close()
            browser.close()
            p.stop()
            return output_path
        except Exception as e:
            if str(e) == IMAGE_SIZE_LIMIT_ERROR:
                raise
            raise ValueError(
                f"Diff PNG/PDF rendering requires a Chromium-compatible browser. Set browser.executablePath or install Chrome/Chromium. {e}"
            )
        finally:
            try:
                await lease["release"]()
            except Exception:
                pass