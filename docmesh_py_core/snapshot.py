from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .security import mask_sensitive_value
from .serialization import to_serializable


def build_settings_snapshot(settings: Any) -> dict[str, Any]:
    serialized = to_serializable(settings)
    if not isinstance(serialized, dict):
        raise TypeError("settings snapshot requires a mapping-like object")
    return _mask_snapshot_value(serialized)


def _mask_snapshot_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _mask_field(str(key), item) for key, item in value.items()}
    if isinstance(value, list):
        return [_mask_snapshot_value(item) for item in value]
    if isinstance(value, str):
        return mask_sensitive_value(value)
    return value


def _mask_field(key: str, value: Any) -> Any:
    lowered = key.lower()
    if isinstance(value, dict):
        return {str(child_key): _mask_field(str(child_key), child_value) for child_key, child_value in value.items()}
    if isinstance(value, list):
        if any(token in lowered for token in ("server", "dsn", "uri", "url", "host", "endpoint")):
            return [_mask_endpoint_like(str(item)) for item in value]
        return [_mask_snapshot_value(item) for item in value]
    if isinstance(value, str):
        if any(token in lowered for token in ("secret", "password", "token", "key")):
            return "***"
        if any(token in lowered for token in ("server", "dsn", "uri", "url", "host", "endpoint")):
            return _mask_endpoint_like(value)
        return mask_sensitive_value(value)
    return value


def _mask_endpoint_like(raw: str) -> str:
    masked = mask_sensitive_value(raw)
    if "://" not in masked or "@" not in masked:
        return masked
    parts = urlsplit(masked)
    if "@" not in parts.netloc:
        return masked
    _, host_part = parts.netloc.rsplit("@", 1)
    return urlunsplit((parts.scheme, f"***@{host_part}", parts.path, parts.query, parts.fragment))
