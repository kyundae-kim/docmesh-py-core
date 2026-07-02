from __future__ import annotations

import asyncio
import json
from urllib.request import urlopen

import pytest

from docmesh_py_core.factories import (
    create_langfuse_client,
    create_milvus_client,
    create_minio_client,
    create_nats_client,
    create_ollama_client,
    create_postgres_client,
    create_sqlite_client,
)
from docmesh_py_core.keycloak import KeycloakAuthService
from test_docmesh_py_core.conftest import (
    docmesh_env_context,
    KeycloakIntegrationConfig,
    KeycloakIntegrationDiscoveryConfig,
    LangfuseIntegrationConfig,
    MilvusIntegrationConfig,
    MinioIntegrationConfig,
    NatsIntegrationConfig,
    OllamaIntegrationConfig,
    PostgresIntegrationConfig,
    SqliteIntegrationConfig,
    keycloak_discovery_is_configured,
    keycloak_token_is_configured,
    require_integration_environment,
    service_is_configured,
)


pytestmark = [pytest.mark.integration]


@pytest.mark.keycloak
def test_keycloak_oidc_discovery_endpoint_is_reachable():
    if not keycloak_discovery_is_configured():
        pytest.skip("KEYCLOAK_URL/KEYCLOAK_REALM not configured for integration testing")

    settings = KeycloakIntegrationDiscoveryConfig()

    issuer = f"{settings.url.rstrip('/')}/realms/{settings.realm}"
    discovery_url = f"{issuer}/.well-known/openid-configuration"

    with urlopen(discovery_url, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))

    assert payload["issuer"] == issuer
    assert payload["token_endpoint"].startswith(issuer)
    assert payload["jwks_uri"].startswith(issuer)


@pytest.mark.keycloak
def test_keycloak_fetch_access_token_against_real_service():
    if not keycloak_token_is_configured():
        pytest.skip("Keycloak token grant settings are incomplete for integration testing")

    keycloak = KeycloakIntegrationConfig()
    auth = KeycloakAuthService(keycloak)

    fetch_kwargs = {}
    if keycloak.token_grant_type == "password":
        fetch_kwargs = {
            "username": keycloak.token_username,
            "password": keycloak.token_password,
        }

    token = auth.fetch_access_token(**fetch_kwargs)

    assert token.access_token
    assert token.token_type
    assert token.expires_in > 0


@pytest.mark.keycloak
def test_keycloak_extract_user_info_from_real_access_token():
    if not keycloak_token_is_configured():
        pytest.skip("Keycloak token grant settings are incomplete for integration testing")

    keycloak = KeycloakIntegrationConfig()
    auth = KeycloakAuthService(keycloak, allowed_algorithms=["RS256"])

    fetch_kwargs = {}
    if keycloak.token_grant_type == "password":
        fetch_kwargs = {
            "username": keycloak.token_username,
            "password": keycloak.token_password,
        }

    token = auth.fetch_access_token(**fetch_kwargs)
    user = auth.extract_user_info(token.access_token)

    assert user.sub
    assert user.claims["iss"] == auth.issuer
    assert user.claims["exp"] > 0


@pytest.mark.health
def test_postgres_wrapper_check_against_real_service():
    require_integration_environment()
    if not service_is_configured("postgres"):
        pytest.skip("PostgreSQL integration settings are not configured")

    postgres = PostgresIntegrationConfig()
    client = create_postgres_client(postgres)

    result = client.check()

    assert result is not None


@pytest.mark.health
def test_sqlite_wrapper_check_with_local_memory_database():
    with docmesh_env_context(
        {
            "DOCMESH_ENV": "integration",
            "SQLITE_PATH": ":memory:",
        },
    ):
        sqlite = SqliteIntegrationConfig()
        client = create_sqlite_client(sqlite)

        result = client.check()

    assert result is not None


@pytest.mark.health
def test_minio_wrapper_check_against_real_service():
    require_integration_environment()
    if not service_is_configured("minio"):
        pytest.skip("MinIO integration settings are not configured")

    minio = MinioIntegrationConfig()
    client = create_minio_client(minio)

    buckets = client.check()

    assert buckets is not None


@pytest.mark.health
def test_milvus_wrapper_check_against_real_service():
    require_integration_environment()
    if not service_is_configured("milvus"):
        pytest.skip("Milvus integration settings are not configured")

    milvus = MilvusIntegrationConfig()
    client = create_milvus_client(milvus)

    collections = client.check()

    assert collections is not None


@pytest.mark.health
def test_ollama_wrapper_check_against_real_service():
    require_integration_environment()
    if not service_is_configured("ollama"):
        pytest.skip("Ollama integration settings are not configured")

    ollama = OllamaIntegrationConfig()
    client = create_ollama_client(ollama)

    response = client.check()

    assert response is not None


@pytest.mark.health
def test_langfuse_wrapper_check_against_real_service():
    require_integration_environment()
    if not service_is_configured("langfuse"):
        pytest.skip("Langfuse integration settings are not configured or disabled")

    langfuse = LangfuseIntegrationConfig()
    client = create_langfuse_client(langfuse)

    result = client.check()

    assert result is not None


@pytest.mark.health
def test_nats_builder_check_against_real_service():
    require_integration_environment()
    if not service_is_configured("nats"):
        pytest.skip("NATS integration settings are not configured")

    nats = NatsIntegrationConfig()
    builder = create_nats_client(nats)

    result = asyncio.run(builder.check())

    assert result is not None
