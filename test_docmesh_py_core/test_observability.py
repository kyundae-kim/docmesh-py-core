from __future__ import annotations

import logging
from unittest.mock import Mock

import pytest

from docmesh_py_core.config import load_settings
from docmesh_py_core.keycloak import KeycloakAuthService, KeycloakTokenTemporaryError
from docmesh_py_core.observability import build_service_log_event
from docmesh_py_core.retry import retry_call


pytestmark = [pytest.mark.unit]


class _FakeClock:
    def __init__(self, values: list[float]):
        self._values = iter(values)

    def __call__(self) -> float:
        return next(self._values)


class _SleepRecorder:
    def __init__(self) -> None:
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


def _settings(*, max_retries: int = 3):
    return load_settings(
        {
            "KEYCLOAK_URL": "https://kc.example.com",
            "KEYCLOAK_REALM": "docmesh",
            "KEYCLOAK_CLIENT_ID": "backend",
            "KEYCLOAK_CLIENT_SECRET": "client-secret",
            "KEYCLOAK_MAX_RETRIES": str(max_retries),
            "POSTGRES_DSN": "postgresql://user:***@db.example.com:5432/app",
            "MINIO_ENDPOINT": "minio.example.com:9000",
            "MINIO_ACCESS_KEY": "minio-access",
            "MINIO_SECRET_KEY": "minio-secret",
            "MILVUS_URI": "http://milvus.example.com:19530",
            "OLLAMA_HOST": "http://ollama.example.com:11434",
            "LANGFUSE_ENABLED": "false",
            "NATS_SERVERS": "nats://n1:4222",
        }
    )


def test_build_service_log_event_masks_errors_and_captures_standard_fields():
    event = build_service_log_event(
        service="keycloak",
        operation="fetch_access_token",
        outcome="temporary_error",
        host="https://kc.example.com",
        latency_ms=125,
        retry_count=2,
        error="token=raw-secret-value",
    )

    assert event == {
        "service": "keycloak",
        "operation": "fetch_access_token",
        "outcome": "temporary_error",
        "host": "https://kc.example.com",
        "latency_ms": 125,
        "retry_count": 2,
        "error": "token=***",
    }


def test_retry_call_retries_temporary_failures_with_exponential_backoff():
    attempts = 0
    sleeper = _SleepRecorder()

    def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise KeycloakTokenTemporaryError("temporary outage")
        return "ok"

    result = retry_call(
        operation,
        retry_on=(KeycloakTokenTemporaryError,),
        max_attempts=3,
        base_delay_seconds=0.5,
        sleep=sleeper,
    )

    assert result == "ok"
    assert attempts == 3
    assert sleeper.calls == [0.5, 1.0]


def test_keycloak_auth_service_retries_temporary_token_failures_and_logs_events():
    http_client = Mock()
    http_client.post.side_effect = [
        KeycloakTokenTemporaryError("token=first-secret"),
        {
            "status_code": 503,
            "json": {"error_description": "client_secret second-secret"},
        },
        {
            "status_code": 200,
            "json": {
                "access_token": "access-token-value",
                "token_type": "Bearer",
                "expires_in": 300,
            },
        },
    ]
    logger = logging.getLogger("docmesh_py_core.tests")
    event_logger = Mock()
    sleeper = _SleepRecorder()
    clock = _FakeClock([10.0, 10.1, 20.0, 20.25, 30.0, 30.4])

    auth = KeycloakAuthService(
        _settings(max_retries=2),
        http_client=http_client,
        logger=logger,
        event_logger=event_logger,
        timer=clock,
        sleep=sleeper,
    )

    token = auth.fetch_access_token()

    assert token.access_token == "access-token-value"
    assert http_client.post.call_count == 3
    assert sleeper.calls == [0.5, 1.0]
    assert event_logger.call_count == 3

    first_event = event_logger.call_args_list[0].args[0]
    second_event = event_logger.call_args_list[1].args[0]
    third_event = event_logger.call_args_list[2].args[0]

    assert first_event["service"] == "keycloak"
    assert first_event["operation"] == "fetch_access_token"
    assert first_event["outcome"] == "temporary_error"
    assert first_event["retry_count"] == 0
    assert first_event["latency_ms"] == 100
    assert "first-secret" not in first_event["error"]
    assert "***" in first_event["error"]

    assert second_event["outcome"] == "temporary_error"
    assert second_event["retry_count"] == 1
    assert second_event["latency_ms"] == 250
    assert "second-secret" not in second_event["error"]
    assert "***" in second_event["error"]

    assert third_event["outcome"] == "success"
    assert third_event["retry_count"] == 2
    assert third_event["latency_ms"] == 400
    assert "error" not in third_event
