from __future__ import annotations
from collections.abc import Mapping
from typing import Any
from .security import mask_sensitive_value
from .function_logging import log_function_boundary
STANDARD_LOG_KEYS = ('service', 'operation', 'outcome', 'host', 'latency_ms', 'retry_count', 'error')

@log_function_boundary()
def build_service_log_event(*, service: str, operation: str, outcome: str, host: str | None=None, latency_ms: int | None=None, retry_count: int | None=None, error: str | None=None, extra: Mapping[str, Any] | None=None) -> dict[str, Any]:
    event: dict[str, Any] = {'service': service, 'operation': operation, 'outcome': outcome}
    if host is not None:
        event['host'] = host
    if latency_ms is not None:
        event['latency_ms'] = latency_ms
    if retry_count is not None:
        event['retry_count'] = retry_count
    if error is not None:
        event['error'] = mask_sensitive_value(error) or '***'
    if extra:
        for key, value in extra.items():
            event[key] = mask_sensitive_value(str(value)) or '***' if _looks_sensitive_key(key) else value
    return event

@log_function_boundary()
def _looks_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any((token in lowered for token in ('password', 'secret', 'token', 'key')))
