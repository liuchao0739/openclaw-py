import os
import json
import http.server
import socketserver
import threading
import time
from typing import Optional, Dict, Any, Callable, Tuple

from .oauth_token import OAuthToken, save_token, load_token
from .oauth_flow import OAuthFlow, create_oauth_flow


class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    code: Optional[str] = None
    state: Optional[str] = None
    error: Optional[str] = None

    def do_GET(self):
        parsed_path = self.path
        if "?" in parsed_path:
            path, query = parsed_path.split("?", 1)
        else:
            path = parsed_path
            query = ""

        params = {}
        if query:
            for param in query.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    params[key] = value

        if "code" in params:
            OAuthCallbackHandler.code = params["code"]
            OAuthCallbackHandler.state = params.get("state")
            self._send_html_response("Success!", "Authentication successful. You can close this window.")
        elif "error" in params:
            OAuthCallbackHandler.error = params["error"]
            self._send_html_response("Error", f"Authentication error: {params['error']}")
        else:
            self._send_html_response("Error", "Invalid callback. No authorization code received.")

    def _send_html_response(self, title: str, body: str):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        html = f"<html><head><title>{title}</title></head><body><h1>{title}</h1><p>{body}</p></body></html>"
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format, *args):
        pass


class OAuthHttpServer:
    def __init__(self, host: str = "localhost", port: int = 3456):
        self.host = host
        self.port = port
        self._server: Optional[socketserver.HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        OAuthCallbackHandler.code = None
        OAuthCallbackHandler.state = None
        OAuthCallbackHandler.error = None

        self._server = socketserver.HTTPServer((self.host, self.port), OAuthCallbackHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def wait_for_code(self, timeout_seconds: int = 300) -> Tuple[Optional[str], Optional[str]]:
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            if OAuthCallbackHandler.code is not None:
                return OAuthCallbackHandler.code, OAuthCallbackHandler.state
            if OAuthCallbackHandler.error is not None:
                return None, None
            time.sleep(0.5)
        return None, None

    @property
    def redirect_url(self) -> str:
        return f"http://{self.host}:{self.port}"


def run_oauth_login_flow(
    config: Optional[Dict[str, Any]] = None,
    on_auth_url: Optional[Callable[[str], None]] = None,
) -> Optional[OAuthToken]:
    flow = create_oauth_flow()
    if not flow:
        return None

    server = OAuthHttpServer()
    try:
        server.start()
        flow.redirect_uri = server.redirect_url
        auth_url = flow.generate_auth_url()

        if on_auth_url:
            on_auth_url(auth_url)
        else:
            print(f"Please visit this URL to authenticate: {auth_url}")

        code, state = server.wait_for_code()
        if not code:
            return None

        token_response = flow.exchange_code(code, state)
        if not token_response:
            return None

        token = OAuthToken.from_response(token_response)
        save_token(token)
        return token
    finally:
        server.stop()


def refresh_token_if_needed(
    config: Optional[Dict[str, Any]] = None,
) -> Optional[OAuthToken]:
    token = load_token()
    if not token:
        return None

    if not token.is_expired():
        return token

    if not token.refresh_token:
        return None

    flow = create_oauth_flow()
    if not flow:
        return None

    response = flow.refresh_token(token.refresh_token)
    if not response:
        return None

    new_token = OAuthToken.from_response(response)
    if new_token.refresh_token is None:
        new_token.refresh_token = token.refresh_token
    save_token(new_token)
    return new_token