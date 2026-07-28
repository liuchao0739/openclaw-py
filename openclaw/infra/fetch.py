from __future__ import annotations

import json
from typing import Any


class HttpResponse:
    def __init__(
        self,
        status: int,
        headers: dict[str, str],
        body: bytes | str,
        url: str = "",
    ):
        self.status = status
        self.headers = headers
        self._body = body
        self.url = url

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    @property
    def text(self) -> str:
        if isinstance(self._body, bytes):
            return self._body.decode("utf-8")
        return self._body

    @property
    def content(self) -> bytes:
        if isinstance(self._body, str):
            return self._body.encode("utf-8")
        return self._body

    def json(self) -> Any:
        return json.loads(self.text)


async def fetch(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: bytes | str | None = None,
    timeout: float | None = None,
    allow_redirects: bool = True,
    max_redirects: int = 10,
    ssl_verify: bool = True,
    proxy: str | None = None,
) -> HttpResponse:
    import urllib.request
    import urllib.error
    import ssl

    req_headers = headers or {}
    data = None
    if body is not None:
        data = body.encode("utf-8") if isinstance(body, str) else body

    req = urllib.request.Request(url, data=data, headers=req_headers, method=method.upper())

    context = ssl.create_default_context()
    if not ssl_verify:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

    try:
        if timeout:
            response = urllib.request.urlopen(req, timeout=timeout, context=context)
        else:
            response = urllib.request.urlopen(req, context=context)

        resp_body = response.read()
        resp_headers = dict(response.headers)
        return HttpResponse(
            status=response.status,
            headers={k.lower(): v for k, v in resp_headers.items()},
            body=resp_body,
            url=response.url,
        )
    except urllib.error.HTTPError as e:
        resp_body = e.read()
        return HttpResponse(
            status=e.code,
            headers={k.lower(): v for k, v in e.headers.items()} if e.headers else {},
            body=resp_body,
            url=url,
        )


class FetchError(Exception):
    pass


class AbortError(FetchError):
    pass
