from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

SENSITIVE_KEYWORDS = (
    "password",
    "passwd",
    "secret",
    "token",
    "apikey",
    "api_key",
    "access_key",
    "client_secret",
)


def is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(keyword in lowered for keyword in SENSITIVE_KEYWORDS)


def mask_sensitive_value(raw: str | None) -> str | None:
    if raw is None:
        return None

    value = str(raw)
    if not value:
        return value

    try:
        parsed = urlsplit(value)
        if parsed.scheme and (parsed.netloc or parsed.path):
            username = parsed.username
            hostname = parsed.hostname or ""
            port = f":{parsed.port}" if parsed.port else ""
            userinfo = f"{username}:***@" if username is not None else ""
            netloc = f"{userinfo}{hostname}{port}"
            query_pairs = []
            for key, query_value in parse_qsl(parsed.query, keep_blank_values=True):
                query_pairs.append((key, "***" if is_sensitive_key(key) else query_value))
            query = urlencode(query_pairs)
            return urlunsplit((parsed.scheme, netloc, parsed.path, query, parsed.fragment))
    except Exception:
        pass

    lowered = value.lower()
    if any(keyword in lowered for keyword in SENSITIVE_KEYWORDS):
        masked = value
        replaced_specific_value = False
        for separator in ("=", ":", " "):
            for keyword in SENSITIVE_KEYWORDS:
                marker = f"{keyword}{separator}"
                lower_marker = marker.lower()
                index = masked.lower().find(lower_marker)
                if index >= 0:
                    start = index + len(marker)
                    end = len(masked)
                    for stop_char in (" ", "&", ",", ";"):
                        next_index = masked.find(stop_char, start)
                        if next_index != -1:
                            end = min(end, next_index)
                    masked = f"{masked[:start]}***{masked[end:]}"
                    replaced_specific_value = True
        return masked if replaced_specific_value else "***"

    return "***"
