from __future__ import annotations

from unittest.mock import Mock

import pytest

from docmesh_py_core.config import load_service_configs as _runtime_load_service_configs
from docmesh_py_core.keycloak import (
    KeycloakAuthService,
    KeycloakTokenAuthenticationError,
    KeycloakTokenTemporaryError,
)
from docmesh_py_core.security import mask_sensitive_value
from test_docmesh_py_core.conftest import apply_docmesh_env


pytestmark = [pytest.mark.unit, pytest.mark.security, pytest.mark.keycloak]


def load_service_configs(env: dict[str, str] | None = None, *, services: set[str] | None = None):
    with pytest.MonkeyPatch.context() as monkeypatch:
        apply_docmesh_env(monkeypatch, env or {})
        return _runtime_load_service_configs(services=services)


def _settings() -> object:
    return load_service_configs(
        {
            "KEYCLOAK_URL": "https://kc.example.com",
            "KEYCLOAK_REALM": "docmesh",
            "KEYCLOAK_CLIENT_ID": "backend",
            "KEYCLOAK_CLIENT_SECRET": "client-secret",
            "KEYCLOAK_PROVISIONING_ENABLED": "true",
            "KEYCLOAK_ADMIN_CLIENT_SECRET": "admin-secret",
            "POSTGRES_DSN": "postgresql://user:***@db.example.com:5432/app",
            "MINIO_ENDPOINT": "minio.example.com:9000",
            "MINIO_ACCESS_KEY": "minio-access",
            "MINIO_SECRET_KEY": "minio-secret",
            "MILVUS_URI": "http://milvus.example.com:19530",
            "OLLAMA_HOST": "http://ollama.example.com:11434",
            "LANGFUSE_HOST": "https://langfuse.example.com",
            "LANGFUSE_PUBLIC_KEY": "public-key",
            "LANGFUSE_SECRET_KEY": "secret-key",
            "NATS_SERVERS": "nats://n1:4222",
            "KEYCLOAK_REALM_ROLES": "reader,writer",
            "KEYCLOAK_CLIENT_ROLES": "admin",
        },
        services={"keycloak"},
    )


def test_keycloak_auth_service_masks_authentication_failures():
    http_client = Mock()
    http_client.post.return_value = {
        "status_code": 401,
        "json": {"error_description": "client_secret invalid-secret"},
    }

    auth = KeycloakAuthService(_settings().keycloak, http_client=http_client)

    with pytest.raises(KeycloakTokenAuthenticationError) as exc_info:
        auth.fetch_access_token()

    assert "invalid-secret" not in str(exc_info.value)
    assert "***" in str(exc_info.value)


def test_keycloak_auth_service_masks_temporary_failures():
    http_client = Mock()
    http_client.post.return_value = {
        "status_code": 503,
        "json": {"error_description": "access_token raw-token-value client_secret leaked-secret"},
    }

    auth = KeycloakAuthService(_settings().keycloak, http_client=http_client)

    with pytest.raises(KeycloakTokenTemporaryError) as exc_info:
        auth.fetch_access_token()

    message = str(exc_info.value)
    assert "raw-token-value" not in message
    assert "leaked-secret" not in message
    assert "***" in message


def test_mask_sensitive_value_masks_raw_bearer_tokens():
    raw_bearer_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTEyMyIsInRva2VuIjoiYWJjMTIzIn0.signature"

    assert mask_sensitive_value(raw_bearer_token) == "***"
