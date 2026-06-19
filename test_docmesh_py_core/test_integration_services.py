from __future__ import annotations

import asyncio
import json
from urllib.request import urlopen

import pytest

from docmesh_py_core.config import load_settings
from docmesh_py_core.factories import ServiceFactoryRegistry
from docmesh_py_core.keycloak import KeycloakAuthService
from test_docmesh_py_core.conftest import (
    integration_env,
    keycloak_discovery_is_configured,
    keycloak_token_is_configured,
    require_integration_environment,
    service_env,
    service_is_configured,
)


pytestmark = [pytest.mark.integration]


@pytest.mark.keycloak
def test_keycloak_oidc_discovery_endpoint_is_reachable():
    require_integration_environment()
    if not keycloak_discovery_is_configured():
        pytest.skip("KEYCLOAK_URL/KEYCLOAK_REALM not configured for integration testing")

    env = integration_env()
    issuer = f"{env['KEYCLOAK_URL'].rstrip('/')}/realms/{env['KEYCLOAK_REALM']}"
    discovery_url = f"{issuer}/.well-known/openid-configuration"

    with urlopen(discovery_url, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))

    assert payload["issuer"] == issuer
    assert payload["token_endpoint"].startswith(issuer)
    assert payload["jwks_uri"].startswith(issuer)


@pytest.mark.keycloak
def test_keycloak_fetch_access_token_against_real_service():
    require_integration_environment()
    if not keycloak_token_is_configured():
        pytest.skip("Keycloak token grant settings are incomplete for integration testing")

    settings = load_settings(service_env("keycloak"))

    token = KeycloakAuthService(settings).fetch_access_token()

    assert token.access_token
    assert token.token_type
    assert token.expires_in > 0


@pytest.mark.health
def test_postgres_wrapper_check_against_real_service():
    require_integration_environment()
    if not service_is_configured("postgres"):
        pytest.skip("PostgreSQL integration settings are not configured")

    settings = load_settings(service_env("postgres"))
    client = ServiceFactoryRegistry(settings).create_client("postgres")

    result = client.check()

    assert result is not None


@pytest.mark.health
def test_sqlite_wrapper_check_with_local_memory_database():
    settings = load_settings(
        {
            "DOCMESH_ENV": "integration",
            "KEYCLOAK_URL": "https://kc.invalid",
            "KEYCLOAK_REALM": "docmesh",
            "KEYCLOAK_CLIENT_ID": "docmesh-client",
            "KEYCLOAK_CLIENT_SECRET": "placeholder-secret",
            "SQLITE_PATH": ":memory:",
            "MINIO_ENDPOINT": "localhost:9000",
            "MINIO_ACCESS_KEY": "placeholder-access-key",
            "MINIO_SECRET_KEY": "placeholder-secret-key",
            "MILVUS_URI": "http://localhost:19530",
            "OLLAMA_HOST": "http://localhost:11434",
            "LANGFUSE_ENABLED": "false",
            "NATS_SERVERS": "nats://localhost:4222",
        }
    )

    client = ServiceFactoryRegistry(settings).create_client("sqlite")

    result = client.check()

    assert result is not None


@pytest.mark.health
def test_minio_wrapper_check_against_real_service():
    require_integration_environment()
    if not service_is_configured("minio"):
        pytest.skip("MinIO integration settings are not configured")

    settings = load_settings(service_env("minio"))
    client = ServiceFactoryRegistry(settings).create_client("minio")

    buckets = client.check()

    assert buckets is not None


@pytest.mark.health
def test_milvus_wrapper_check_against_real_service():
    require_integration_environment()
    if not service_is_configured("milvus"):
        pytest.skip("Milvus integration settings are not configured")

    settings = load_settings(service_env("milvus"))
    client = ServiceFactoryRegistry(settings).create_client("milvus")

    collections = client.check()

    assert collections is not None


@pytest.mark.health
def test_ollama_wrapper_check_against_real_service():
    require_integration_environment()
    if not service_is_configured("ollama"):
        pytest.skip("Ollama integration settings are not configured")

    settings = load_settings(service_env("ollama"))
    client = ServiceFactoryRegistry(settings).create_client("ollama")

    response = client.check()

    assert response is not None


@pytest.mark.health
def test_langfuse_wrapper_check_against_real_service():
    require_integration_environment()
    if not service_is_configured("langfuse"):
        pytest.skip("Langfuse integration settings are not configured or disabled")

    settings = load_settings(service_env("langfuse"))
    client = ServiceFactoryRegistry(settings).create_client("langfuse")

    result = client.check()

    assert result is not None


@pytest.mark.health
def test_nats_builder_check_against_real_service():
    require_integration_environment()
    if not service_is_configured("nats"):
        pytest.skip("NATS integration settings are not configured")

    settings = load_settings(service_env("nats"))
    builder = ServiceFactoryRegistry(settings).create_client("nats")

    result = asyncio.run(builder.check())

    assert result is not None
