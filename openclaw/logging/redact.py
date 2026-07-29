"""Redaction helpers scrub secrets and sensitive identifiers from log output.

Mirrors src/logging/redact.ts.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from openclaw.logging.config import read_logging_config
from openclaw.logging.redact_bounded import replace_pattern_bounded

RedactSensitiveMode = Literal["off", "tools"]
RedactPattern = str

DEFAULT_REDACT_MODE: RedactSensitiveMode = "tools"
DEFAULT_REDACT_MIN_LENGTH = 18
DEFAULT_REDACT_KEEP_START = 6
DEFAULT_REDACT_KEEP_END = 4

AUTH_QUERY_KEYS = r"access[-_]?token|auth[-_]?token|hook[-_]?token|refresh[-_]?token|id[-_]?token|api[-_]?key|apikey|client[-_]?secret|app[-_]?secret|private[-_]?key|credential|authorization|token|secret|password|pass|passwd|auth|jwt|session|code|signature|x[-_]?amz[-_]?(?:signature|security[-_]?token)"

PAYMENT_CREDENTIAL_QUERY_KEYS = r"card[-_]?number|card[-_]?cvc|card[-_]?cvv|cvc|cvv|security[-_]?code|payment[-_]?credential|shared[-_]?payment[-_]?token"

PAYMENT_CREDENTIAL_ENV_KEYS = r"CARD[_-]?NUMBER|CARD[_-]?CVC|CARD[_-]?CVV|CVC|CVV|SECURITY[_-]?CODE|PAYMENT[_-]?CREDENTIAL|SHARED[_-]?PAYMENT[_-]?TOKEN"

STANDALONE_ASSIGNMENT_SECRET_KEYS = r"access_token|refresh_token|id_token|auth[-_]?token|hook[-_]?token|api[-_]?key|client[-_]?secret|app[-_]?secret|private[-_]?key|authorization|jwt|token|secret|password|pass|passwd|credential|" + PAYMENT_CREDENTIAL_QUERY_KEYS

FORM_BODY_KEY_INVISIBLE_CHARS = r"\p{C}\u00A0\u1680\u2000-\u200A\u202F\u205F\u3000\u115F\u1160\u3164\uFFA0"
FORM_BODY_KEY = r"[" + FORM_BODY_KEY_INVISIBLE_CHARS + r"+]*(?:[A-Za-z_]|%[0-9A-Fa-f]{2})(?:[A-Za-z0-9_.-]|%[0-9A-Fa-f]{2}|[" + FORM_BODY_KEY_INVISIBLE_CHARS + r"+])*"
FORM_BODY_VALUE = r"[^&\s<>]*"
URL_QUERY_VALUE = r"[^&#\s<>]*"

BODY_SECRET_KEYS = {
    "access_token", "auth_token", "hook_token", "refresh_token", "id_token",
    "token", "api_key", "apikey", "client_secret", "app_secret", "password",
    "pass", "passwd", "auth", "jwt", "session", "code", "signature",
    "x_amz_signature", "x_amz_security_token", "secret", "credential",
    "private_key", "authorization", "key", "card_number", "card_cvc",
    "card_cvv", "cvc", "cvv", "security_code", "payment_credential",
    "shared_payment_token",
}

SECRET_VALUE_QUOTE_CHARS = {'"', "'", "`"}
SECRET_VALUE_TRAILING_DELIMITER_RE = re.compile(r"""(["'`,;)}\]]+)$""")
SECRET_VALUE_SUFFIX_RE = re.compile(r"""^["'`,;)}\]]*$""")

FORM_BODY_KEY_SEPARATOR_RE = re.compile(r"[\p{C}\p{Z}\u115F\u1160\u3164\uFFA0+]", re.UNICODE)
FORM_BODY_PERCENT_ESCAPE_RE = re.compile(r"%[0-9A-Fa-f]{2}")

URL_QUERY_PAIR_RE = re.compile(
    r"([?&])(" + FORM_BODY_KEY + r")=(" + URL_QUERY_VALUE + r")",
    re.UNICODE,
)

STRUCTURED_SECRET_FIELD_RE = re.compile(
    r"^(?:api[-_]?key|apiKey|token|secret|password|passwd|credential|authorization|private[-_]?key|privateKey|access[-_]?token|accessToken|refresh[-_]?token|refreshToken|id[-_]?token|idToken|auth[-_]?token|authToken|client[-_]?secret|clientSecret|app[-_]?secret|appSecret|secret[-_]?value|secretValue|raw[-_]?secret|rawSecret|secret[-_]?input|secretInput|key[-_]?material|keyMaterial|"
    + PAYMENT_CREDENTIAL_QUERY_KEYS
    + r"|cardNumber|card_number|cardCvc|card_cvc|cardCvv|card_cvv|cvc|cvv|securityCode|security_code|paymentCredential|payment_credential|sharedPaymentToken|shared_payment_token)$",
    re.IGNORECASE,
)

STRUCTURED_SECRET_ENV_FIELD_RE = re.compile(
    r"^(?:(?:[A-Z0-9]+[_-])+(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD)|API[_-]?KEY|TOKEN|SECRET|PASSWORD|PASSWD|"
    + PAYMENT_CREDENTIAL_ENV_KEYS
    + r")$",
    re.IGNORECASE,
)

APP_SPECIFIC_PASSWORD_RE = re.compile(r"\b([a-z]{4}-[a-z]{4}-[a-z]{4}-[a-z]{4})\b", re.IGNORECASE)

BENIGN_APP_PASSWORD_WORDS = {
    "case", "claw", "demo", "file", "main", "name", "open", "path", "slug", "test",
}

DEFAULT_REDACT_PATTERNS: list[str] = [
    r"\b[A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD|" + PAYMENT_CREDENTIAL_ENV_KEYS + r")\b\s*[=:]\s*(["']?)([^\s"'\\]+)\1",
    r"\b[A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD|" + PAYMENT_CREDENTIAL_ENV_KEYS + r")\b\s*[=:]\s*\\+(["'])([^\s"'\\]+)\\+\1",
    r"[?&](?:" + AUTH_QUERY_KEYS + r"|" + PAYMENT_CREDENTIAL_QUERY_KEYS + r")=([^&#\s<>]+)",
    r'"(?:apiKey|api_key|token|secret|password|passwd|credential|authorization|accessToken|access_token|refreshToken|refresh_token|idToken|id_token|authToken|auth_token|clientSecret|client_secret|privateKey|private_key|secret_value|raw_secret|secret_input|key_material|' + PAYMENT_CREDENTIAL_QUERY_KEYS + r')"\s*:\s*"([^"]+)"',
    r'(^|[\s,{])["\']?(?:api[-_]key|access[-_]token|refresh[-_]token|id[-_]token|authToken|auth[-_]token|clientSecret|client[-_]secret|appSecret|app[-_]secret|private[-_]key|credential|authorization|secret[-_]value|raw[-_]secret|secret[-_]input|key[-_]material)["\']?\s*[:=]\s*(["\'])([^"\'\r\n]+)\2',
    r'(^|[\s,{])["\']?(?:authorization|proxy-authorization|cookie|set-cookie|x-api-key|x-auth-token)["\']?\s*[:=]\s*(["\'])([^"\'\r\n]+)\2',
    r"--(?:api[-_]?key|hook[-_]?token|access[-_]?token|refresh[-_]?token|id[-_]?token|token|secret|password|passwd|credential|private[-_]?key|client[-_]?secret|" + PAYMENT_CREDENTIAL_QUERY_KEYS + r")\s+(?!(?:or|and)\b(?=\s+--))(["']?)([^\s\"']+)\1",
    r"Authorization\s*[:=]\s*Bearer\s+([A-Za-z0-9._\-+=]+)",
    r"Authorization\s*[:=]\s*Basic\s+([A-Za-z0-9+/=]+)",
    r"Authorization\s*[:=]\s*Bot\s+([A-Za-z0-9._\-+=]{18,})",
    r"(?:X-OpenClaw-Token|x-pomerium-jwt-assertion|X-Api-Key|X-Auth-Token)\s*[:=]\s*([^\s\"',;]+)",
    r"\bBearer\s+([A-Za-z0-9._\-+=]{18,})\b",
    r"\b(?:https?|wss?|ftp)://[^/\s:@]*:([^/\s@]+)@",
    r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|rediss?|amqps?)://[^:\s/@]*:([^@\s]+)@",
    r"(^|[\s,;])(?:" + AUTH_QUERY_KEYS + r"|" + PAYMENT_CREDENTIAL_QUERY_KEYS + r")=([^&\s]+)(?=&[A-Za-z_][A-Za-z0-9_.-]*=)",
    r"(^|[\s,;])(?:" + STANDALONE_ASSIGNMENT_SECRET_KEYS + r")=(["'`])((?:(?!\2)[^\r\n])+)\2",
    r"(^|[\s,;])(?:" + STANDALONE_ASSIGNMENT_SECRET_KEYS + r")=(["'`]?[^\s&#\"'`<>]+)",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----",
    r"\b(sk-[A-Za-z0-9_-]{8,})\b",
    r"(ghp_[A-Za-z0-9]{10,})",
    r"(github_pat_[A-Za-z0-9_]{10,})",
    r"(gho_[A-Za-z0-9]{10,})",
    r"(ghu_[A-Za-z0-9]{10,})",
    r"(ghs_[A-Za-z0-9]{10,})",
    r"(ghr_[A-Za-z0-9]{10,})",
    r"(glpat-[A-Za-z0-9._=\-]{20,})",
    r"(gloas-[A-Fa-f0-9]{32,})",
    r"(xox[baprs]-[A-Za-z0-9-]{10,})",
    r"(xapp-[A-Za-z0-9-]{10,})",
    r"(https://hooks\.slack\.com/(?:services/T[A-Z0-9]+/B[A-Z0-9]+|workflows/T[A-Z0-9]+/A[A-Z0-9]+/[0-9]{17,19})/[A-Za-z0-9]{20,})",
    r"(https://discord(?:app)?\.com/api/webhooks/[0-9]{17,20}/[A-Za-z0-9_-]{60,})",
    r"(gsk_[A-Za-z0-9_-]{10,})",
    r"(AIza[0-9A-Za-z\-_]{20,})",
    r"(ya29\.[0-9A-Za-z_\-./+=]{10,})",
    r"(1//0[0-9A-Za-z_\-./+=]{10,})",
    r"(eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})",
    r"(pplx-[A-Za-z0-9_-]{10,})",
    r"(fal_[A-Za-z0-9_-]{10,})",
    r"(fc-[A-Za-z0-9]{10,})",
    r"(bb_live_[A-Za-z0-9_-]{10,})",
    r"(sk_live_[A-Za-z0-9]{10,})",
    r"(sk_test_[A-Za-z0-9]{10,})",
    r"(rk_live_[A-Za-z0-9]{10,})",
    r"(SG\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})",
    r"(npm_[A-Za-z0-9]{10,})",
    r"(pypi-[A-Za-z0-9_-]{10,})",
    r"(dop_v1_[A-Za-z0-9]{10,})",
    r"(doo_v1_[A-Za-z0-9]{10,})",
    r"(dor_v1_[A-Za-z0-9]{10,})",
    r"(dp\.(?:ct|pt|sa|scim|audit)\.[A-Za-z0-9]{40,44})",
    r"(dp\.st\.[A-Za-z0-9]{40,44})",
    r"(dckr_(?:pat|oat)_[A-Za-z0-9_-]{27,32})",
    r"(bkua_[a-z0-9]{40})",
    r"(CCIPAT_[A-Za-z0-9]{22}_[A-Fa-f0-9]{40})",
    r"(sbp_[a-z0-9]{40})",
    r"(dd[pw]_[A-Za-z0-9]{36})",
    r"(glsa_[A-Za-z0-9_]{41})",
    r"(nfp_[A-Za-z0-9_]{36})",
    r"(CFPAT-[A-Za-z0-9_\-]{40,})",
    r"(BBDC-[A-Za-z0-9+/@_-]{40,50})",
    r"(HRKU-AA[A-Za-z0-9_-]{20,})",
    r"(pat-(?:eu|na)1-[A-Za-z0-9]{8}\-[A-Za-z0-9]{4}\-[A-Za-z0-9]{4}\-[A-Za-z0-9]{4}\-[A-Za-z0-9]{12})",
    r"(apify_api_[A-Za-z0-9\-]{20,})",
    r"(fio-u-[A-Za-z0-9_-]{40,})",
    r"(^|[^A-Za-z0-9_])(am_[A-Za-z0-9_-]{10,})",
    r"(^|[^A-Za-z0-9_])(sk_[A-Za-z0-9_]{10,})",
    r"(tvly-[A-Za-z0-9]{10,})",
    r"(exa_[A-Za-z0-9]{10,})",
    r"(syt_[A-Za-z0-9]{10,})",
    r"(retaindb_[A-Za-z0-9]{10,})",
    r"(hsk-[A-Za-z0-9]{10,})",
    r"(mem0_[A-Za-z0-9]{10,})",
    r"(brv_[A-Za-z0-9]{10,})",
    r"(xai-[A-Za-z0-9]{30,})",
    r"(AKIA[A-Z0-9]{16})",
    r"(ASIA[A-Z0-9]{16})",
    r"(AKID[A-Za-z0-9]{10,})",
    r"(LTAI[A-Za-z0-9]{10,})",
    r"(hf_[A-Za-z0-9]{10,})",
    r"(api_org_[A-Za-z0-9]{20,})",
    r"(r8_[A-Za-z0-9]{10,})",
    r"\bbot(\d{6,}:[A-Za-z0-9_-]{20,})\b",
    r"\b(\d{6,}:[A-Za-z0-9_-]{20,})\b",
]

DEFAULT_REDACT_PREFILTER_RE = re.compile(
    r"KEY|TOKEN|SECRET|PASSWORD|PASSWD|AUTH|COOKIE|SIGNATURE|CREDENTIAL|CARD|CVC|CVV|PAYMENT|PRIVATE KEY"
    r"|security[-_]?code|\bpass=|jwt=|session=|code="
    r"|\bBearer\s+"
    r"|://[^/\s:@]*:[^/\s@]+@"
    r"|sk-|gh[opsur]_|github_pat_|glpat-|gloas-|xox[baprs]-|xapp-|hooks\.slack\.com|discord|gsk_|AIza|ya29\.|1//0|eyJ|pplx-|fal_|fc-|bb_live_|gAAAA|[sr]k_(?:live|test)_|\bSG\.|npm_|pypi-|do[opr]_v1_|dp\.(?:ct|pt|sa|st|scim|audit)\.|dckr_|bkua_|CCIPAT_|sbp_|dapi[0-9a-f]|dd[pw]_|glsa_|nfp_|CFPAT-|ATCTT3|ATATT|ATBB|BBDC-|HRKU-|pat-(?:eu|na)1-|apify_api_|FlyV1|fio-u-|tvly-|exa_|syt_|retaindb_|mem0_|brv_|xai-"
    r"|(?:^|[^A-Za-z0-9_])(?:am_|sk_)"
    r"|A[KS]IA[A-Z0-9]|AKID|LTAI|hf_|api_org_|r8_"
    r"|\bbot\d{6,}:|\b\d{6,}:[A-Za-z0-9_-]{20,}"
    r"|%[0-9A-Fa-f]{2}[A-Za-z0-9_%.-]*=",
    re.IGNORECASE,
)

_default_resolved_patterns: list[re.Pattern] | None = None


class RedactOptions(dict):
    mode: Any
    patterns: Any


class ResolvedRedactOptions(dict):
    mode: Any
    patterns: Any
    redactFormBodies: Any


def _normalize_mode(value: str | None = None) -> RedactSensitiveMode:
    return "off" if value == "off" else DEFAULT_REDACT_MODE


def _parse_pattern(raw: RedactPattern) -> re.Pattern | None:
    if not raw or not raw.strip():
        return None
    match = re.match(r"^/(.+)/([gimsuy]*)$", raw)
    if match:
        source = match.group(1)
        flags = match.group(2)
        if "g" not in flags:
            flags = flags + "g"
        try:
            flag = 0
            if "i" in flags:
                flag |= re.IGNORECASE
            if "m" in flags:
                flag |= re.MULTILINE
            if "s" in flags:
                flag |= re.DOTALL
            if "u" in flags:
                flag |= re.UNICODE
            return re.compile(source, flag)
        except re.error:
            return None
    try:
        return re.compile(raw, re.IGNORECASE)
    except re.error:
        return None


def _resolve_patterns(value: list[RedactPattern] | None = None) -> list[re.Pattern]:
    global _default_resolved_patterns
    if not value or len(value) == 0:
        if _default_resolved_patterns is None:
            _default_resolved_patterns = [p for p in (_parse_pattern(p) for p in DEFAULT_REDACT_PATTERNS) if p is not None]
        return _default_resolved_patterns
    return [p for p in (_parse_pattern(p) for p in value) if p is not None]


def _includes_default_redact_patterns(value: list[RedactPattern] | None = None) -> bool:
    if not value or len(value) == 0:
        return True
    source = set(v for v in value if isinstance(v, str))
    return all(p in source for p in DEFAULT_REDACT_PATTERNS)


def _mask_token(token: str) -> str:
    if token == "***":
        return token
    if len(token) < DEFAULT_REDACT_MIN_LENGTH:
        return "***"
    start = token[:DEFAULT_REDACT_KEEP_START]
    end = token[-DEFAULT_REDACT_KEEP_END:]
    return f"{start}\u2026{end}"


def _split_secret_value_for_mask(token: str) -> dict[str, Any]:
    opening_quote = token[0] if token else ""
    if opening_quote in SECRET_VALUE_QUOTE_CHARS:
        closing_quote_index = token.rfind(opening_quote)
        if closing_quote_index > 0:
            suffix = token[closing_quote_index + 1:]
            if SECRET_VALUE_SUFFIX_RE.match(suffix):
                return {
                    "maskable": token[1:closing_quote_index],
                    "suffix": suffix,
                    "maskStart": 0,
                    "maskEnd": closing_quote_index + 1,
                }
        token_without_leading_quote = token[1:]
        trailing_delimiter_match = SECRET_VALUE_TRAILING_DELIMITER_RE.search(token_without_leading_quote)
        trailing_delimiter = trailing_delimiter_match.group(1) if trailing_delimiter_match else ""
        if trailing_delimiter and len(trailing_delimiter) < len(token_without_leading_quote):
            maskable = token_without_leading_quote[: -len(trailing_delimiter)]
        else:
            maskable = token_without_leading_quote
        return {
            "maskable": maskable,
            "suffix": trailing_delimiter if trailing_delimiter and len(trailing_delimiter) < len(token_without_leading_quote) else "",
            "maskStart": 0,
            "maskEnd": 1 + len(maskable),
        }
    trailing_delimiter_match = SECRET_VALUE_TRAILING_DELIMITER_RE.search(token)
    trailing_delimiter = trailing_delimiter_match.group(1) if trailing_delimiter_match else ""
    if trailing_delimiter and len(trailing_delimiter) < len(token):
        maskable = token[: -len(trailing_delimiter)]
    else:
        maskable = token
    return {
        "maskable": maskable,
        "suffix": "" if maskable == token else trailing_delimiter,
        "maskStart": 0,
        "maskEnd": len(maskable),
    }


def _mask_secret_value(token: str, options: dict[str, bool] | None = None) -> str:
    split = _split_secret_value_for_mask(token)
    hinted = (options or {}).get("hinted", False)
    masked = _mask_token(split["maskable"]) if hinted else "***"
    return f"{masked}{split['suffix']}"


def _normalize_sensitive_key_name(value: str) -> str:
    stripped = FORM_BODY_KEY_SEPARATOR_RE.sub("", value)
    try:
        from urllib.parse import unquote
        decoded = unquote(stripped)
        stripped = FORM_BODY_KEY_SEPARATOR_RE.sub("", decoded)
    except Exception:
        pass
    return stripped.lower().replace("-", "_")


def _is_sensitive_body_key(key: str) -> bool:
    return _normalize_sensitive_key_name(key) in BODY_SECRET_KEYS


def _has_encoded_or_invisible_form_key(key: str) -> bool:
    return bool(FORM_BODY_PERCENT_ESCAPE_RE.search(key)) or FORM_BODY_KEY_SEPARATOR_RE.sub("", key) != key


def _redact_form_encoded_pairs(
    value: str,
    options: dict[str, Any] | None = None,
) -> str:
    pairs = value.split("&")
    result = []
    for pair in pairs:
        equals_index = pair.find("=")
        if equals_index < 0:
            result.append(pair)
            continue
        key = pair[:equals_index]
        if (options or {}).get("onlyEncodedOrInvisibleKeys") and not _has_encoded_or_invisible_form_key(key):
            result.append(pair)
            continue
        if not _is_sensitive_body_key(key):
            result.append(pair)
            continue
        token = pair[equals_index + 1:]
        masked = _mask_secret_value(token, {"hinted": (options or {}).get("maskValues") == "hinted"})
        result.append(f"{key}={masked}")
    return "&".join(result)


def _redact_url_query_pairs(text: str) -> str:
    if not text or "?" not in text:
        return text

    def replacer(match: re.Match) -> str:
        prefix = match.group(1)
        key = match.group(2)
        token = match.group(3)
        if not _has_encoded_or_invisible_form_key(key) or not _is_sensitive_body_key(key):
            return match.group(0)
        return f"{prefix}{key}={_mask_secret_value(token, {'hinted': True})}"

    return URL_QUERY_PAIR_RE.sub(replacer, text)


def _redact_pem_block(block: str) -> str:
    lines = [l for l in block.split("\n") if l.strip()]
    if len(lines) < 2:
        return "***"
    return f"{lines[0]}\n\u2026redacted\u2026\n{lines[-1]}"


def _is_shell_reference_to_key(key: str, value: str) -> bool:
    if not re.match(r"^[A-Z_][A-Z0-9_]*$", key):
        return False
    bare = re.match(r"^\$([A-Z_][A-Z0-9_]*)$", value)
    if bare:
        return bare.group(1) == key
    braced = re.match(r"^\$\{([A-Z_][A-Z0-9_]*)(?::[-=?+])?\}$", value)
    return bool(braced and braced.group(1) == key)


def _select_secret_capture(match: str, groups: list[str]) -> dict[str, Any]:
    tokens = [(i, v) for i, v in enumerate(groups) if isinstance(v, str) and len(v) > 0]
    if len(tokens) > 1:
        selected = tokens[-1]
    elif tokens:
        selected = tokens[0]
    else:
        selected = (-1, match)
    return {"index": selected[0], "value": selected[1], "captureCount": len(tokens)}


def _redact_match(
    match: str,
    groups: list[str],
    pattern: re.Pattern,
    context: dict[str, Any] | None = None,
) -> str:
    if "PRIVATE KEY-----" in match:
        return _redact_pem_block(match)
    selected = _select_secret_capture(match, groups)
    token = selected["value"]
    split = _split_secret_value_for_mask(token)
    if split["maskable"] == "***":
        return match
    masked = _mask_secret_value(token, {"hinted": True})
    if token == match:
        return masked
    token_index = match.rfind(token)
    if token_index < 0:
        return match
    return f"{match[:token_index]}{masked}{match[token_index + len(token):]}"


def _redact_text(
    text: str,
    patterns: list[re.Pattern],
    options: dict[str, bool] | None = None,
) -> str:
    next_text = text
    if (options or {}).get("redactFormBodies"):
        next_text = _redact_url_query_pairs(next_text)
    for pattern in patterns:
        def replacer(match: re.Match) -> str:
            groups = [g if g is not None else "" for g in match.groups()]
            return _redact_match(match.group(0), groups, pattern)
        next_text = pattern.sub(replacer, next_text)
    return next_text


def _could_match_default_redact_patterns(text: str) -> bool:
    return bool(DEFAULT_REDACT_PREFILTER_RE.search(text))


def _resolve_config_redaction() -> RedactOptions:
    cfg = read_logging_config()
    return RedactOptions(
        mode=_normalize_mode(cfg.get("redactSensitive") if cfg else None),
        patterns=cfg.get("redactPatterns") if cfg else None,
    )


def resolve_redact_options(options: RedactOptions | None = None) -> ResolvedRedactOptions:
    resolved = options if options is not None else _resolve_config_redaction()
    mode = _normalize_mode(resolved.get("mode"))
    if mode == "off":
        return ResolvedRedactOptions(mode=mode, patterns=[], redactFormBodies=False)
    patterns = _resolve_patterns(resolved.get("patterns"))
    return ResolvedRedactOptions(
        mode=mode,
        patterns=patterns,
        redactFormBodies=len(patterns) > 0 and _includes_default_redact_patterns(resolved.get("patterns")),
    )


def redact_sensitive_text(text: str, options: RedactOptions | None = None) -> str:
    if not text:
        return text
    resolved_options = options if options is not None else _resolve_config_redaction()
    if _normalize_mode(resolved_options.get("mode")) == "off":
        return text
    if not resolved_options.get("patterns") and not _could_match_default_redact_patterns(text):
        return text
    resolved = resolve_redact_options(resolved_options)
    if not resolved["patterns"]:
        return text
    return _redact_text(text, resolved["patterns"], {"redactFormBodies": resolved["redactFormBodies"]})


def _resolve_tool_payload_redaction(logging_config: dict[str, Any] | None = None) -> RedactOptions:
    user_patterns = (logging_config or {}).get("redactPatterns") if logging_config else None
    patterns = [*user_patterns, *DEFAULT_REDACT_PATTERNS] if user_patterns and len(user_patterns) > 0 else None
    return RedactOptions(mode="tools", patterns=patterns)


def redact_tool_payload_text(text: str) -> str:
    return redact_tool_payload_text_with_config(text, read_logging_config())


def redact_tool_payload_text_with_config(text: str, logging_config: dict[str, Any] | None = None) -> str:
    if not text:
        return text
    return redact_sensitive_text(text, _resolve_tool_payload_redaction(logging_config))


def redact_tool_detail(detail: str) -> str:
    return redact_tool_payload_text(detail)


def is_sensitive_field_key(key: str) -> bool:
    return bool(STRUCTURED_SECRET_FIELD_RE.match(key)) or bool(STRUCTURED_SECRET_ENV_FIELD_RE.match(key))


def _redact_sensitive_field_value_with_options(
    key: str,
    value: str,
    options: RedactOptions,
) -> str:
    resolved = resolve_redact_options(options)
    if resolved["mode"] == "off":
        return value
    redacted = _redact_text(value, resolved["patterns"], {"redactFormBodies": resolved["redactFormBodies"]})
    if redacted != value:
        return redacted
    if is_sensitive_field_key(key):
        if _is_shell_reference_to_key(key, value):
            return value
        return _mask_token(value)
    return value


def redact_sensitive_field_value(
    key: str,
    value: str,
    options: RedactOptions | None = None,
) -> str:
    return _redact_sensitive_field_value_with_options(
        key, value, options if options is not None else _resolve_tool_payload_redaction()
    )


def redact_sensitive_field_value_with_config(
    key: str,
    value: str,
    logging_config: dict[str, Any] | None = None,
) -> str:
    return _redact_sensitive_field_value_with_options(
        key, value, _resolve_tool_payload_redaction(logging_config)
    )


def _is_plain_redactable_object(value: Any) -> bool:
    return isinstance(value, dict)


def _redact_structured_secret_value(
    key: str,
    value: Any,
    seen: set[int],
    options: RedactOptions,
) -> Any:
    if isinstance(value, str):
        return _redact_sensitive_field_value_with_options(key, value, options)
    if value is None:
        return value
    if isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, list):
        value_id = id(value)
        if value_id in seen:
            return "[Circular]"
        seen.add(value_id)
        out = [_redact_structured_secret_value(key, entry, seen, options) for entry in value]
        seen.discard(value_id)
        return out
    if isinstance(value, dict):
        value_id = id(value)
        if value_id in seen:
            return "[Circular]"
        if not _is_plain_redactable_object(value):
            return value
        seen.add(value_id)
        out: dict[str, Any] = {}
        for nested_key, nested_value in value.items():
            out[nested_key] = _redact_structured_secret_value(nested_key, nested_value, seen, options)
        seen.discard(value_id)
        return out
    return value


def redact_secrets(value: Any) -> Any:
    options = _resolve_tool_payload_redaction()
    if isinstance(value, str):
        return redact_sensitive_text(value, options)
    if value is None:
        return value
    if not isinstance(value, (dict, list)):
        return value
    return _redact_structured_secret_value("", value, set(), options)


def get_default_redact_patterns() -> list[str]:
    return list(DEFAULT_REDACT_PATTERNS)


def redact_sensitive_lines(lines: list[str], resolved: ResolvedRedactOptions) -> list[str]:
    if resolved["mode"] == "off" or not resolved["patterns"] or len(lines) == 0:
        return lines
    redacted_lines = (
        [_redact_form_body(_redact_url_query_pairs(line)) for line in lines]
        if resolved["redactFormBodies"]
        else lines
    )
    return _redact_text("\n".join(redacted_lines), resolved["patterns"]).split("\n")


def _redact_form_body(text: str) -> str:
    if not text:
        return text
    return _redact_form_encoded_pairs(text)


def compute_sensitive_redaction_bitmap(
    text: str,
    resolved: ResolvedRedactOptions,
) -> list[bool]:
    bitmap = [False] * len(text)
    if resolved["mode"] == "off" or not resolved["patterns"] or not text:
        return bitmap
    for pattern in resolved["patterns"]:
        for match in pattern.finditer(text):
            full_match = match.group(0)
            start = match.start()
            if "PRIVATE KEY-----" in full_match:
                for i in range(start, min(start + len(full_match), len(bitmap))):
                    bitmap[i] = True
                continue
            groups = [g if g is not None else "" for g in match.groups()]
            selected = _select_secret_capture(full_match, groups)
            token_start = full_match.rfind(selected["value"]) if selected["value"] != full_match else 0
            if token_start < 0:
                continue
            split = _split_secret_value_for_mask(selected["value"])
            for i in range(
                max(0, start + token_start + split["maskStart"]),
                min(len(bitmap), start + token_start + split["maskEnd"]),
            ):
                bitmap[i] = True
    return bitmap


__all__ = [
    "RedactSensitiveMode",
    "RedactPattern",
    "RedactOptions",
    "ResolvedRedactOptions",
    "resolve_redact_options",
    "redact_sensitive_text",
    "redact_tool_detail",
    "redact_tool_payload_text",
    "redact_tool_payload_text_with_config",
    "is_sensitive_field_key",
    "redact_sensitive_field_value",
    "redact_sensitive_field_value_with_config",
    "redact_secrets",
    "get_default_redact_patterns",
    "redact_sensitive_lines",
    "compute_sensitive_redaction_bitmap",
]
