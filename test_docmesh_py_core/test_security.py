from __future__ import annotations

from unittest.mock import Mock

import pytest

from docmesh_py_core.config import load_settings
from docmesh_py_core.keycloak import KeycloakAuthService, KeycloakTokenAuthenticationError


pytestmark = [pytest.mark.security, pytest.mark.keycloak]


def _settings() -> object:
    return load_settings(
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
        }
    )


def test_keycloak_auth_service_masks_authentication_failures():
    http_client = Mock()
    http_client.post.return_value = {
        "status_code": 401,
        "json": {"error_description": "client_secret invalid-secret"},
    }

    auth = KeycloakAuthService(_settings(), http_client=http_client)

    with pytest.raises(KeycloakTokenAuthenticationError) as exc_info:
        auth.fetch_access_token()

    assert "invalid-secret" not in str(exc_info.value)
    assert "***" in str(exc_info.value)
