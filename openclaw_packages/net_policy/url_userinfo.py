from urllib.parse import urlparse, urlunparse


def strip_url_userinfo(value):
    try:
        parsed = urlparse(value)
        if not parsed.username and not parsed.password:
            return value
        netloc = parsed.hostname or ""
        if parsed.port is not None:
            netloc = f"{netloc}:{parsed.port}"
        parsed = parsed._replace(netloc=netloc)
        return urlunparse(parsed)
    except Exception:
        return value
