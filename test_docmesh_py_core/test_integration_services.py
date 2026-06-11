from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any
from urllib.request import urlopen

import pytest

from docmesh_py_core.config import load_settings
from docmesh_py_core.factories import ServiceFactoryRegistry
from docmesh_py_core.keycloak import KeycloakAuthService


pytestmark = [pytest.mark.integration]


INTEGRATION_ENV_NAME = "integration"


def _parse_env_file(path: Path) -> dict[str, str]:
    parsed: dict[str, str] = {}
    if not path.exists():
        return parsed

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value and value[0] == value[-1] and value[0] in {"\"", "'"}:
            value = value[1:-1]
        parsed[key] = value
    return parsed


def _integration_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for candidate in (Path(".env.integration"), Path(".env")):
        env.update(_parse_env_file(candidate))
    env.update({key: value for key, value in os.environ.items() if value})
    return env


def _base_env() -> dict[str, str]:
    return {
        "DOCMESH_ENV": "integration",
        "DOCMESH_HEALTHCHECK_ENABLED": "true",
        "KEYCLOAK_URL": "https://kc.invalid",
        "KEYCLOAK_REALM": "docmesh",
        "KEYCLOAK_CLIENT_ID": "docmesh-client",
        "KEYCLOAK_CLIENT_SECRET": "placeholder-secret",
        "KEYCLOAK_VERIFY_SSL": "true",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "docmesh",
        "POSTGRES_USER": "docmesh",
        "POSTGRES_PASSWORD": "placeholder-password",
        "POSTGRES_SSLMODE": "prefer",
        "MINIO_ENDPOINT": "localhost:9000",
        "MINIO_ACCESS_KEY": "placeholder-access-key",
        "MINIO_SECRET_KEY": "placeholder-secret-key",
        "MINIO_SECURE": "false",
        "MILVUS_URI": "http://localhost:19530",
        "OLLAMA_HOST": "http://localhost:11434",
        "LANGFUSE_ENABLED": "false",
        "NATS_SERVERS": "nats://localhost:4222",
    }


SERVICE_ENV_KEYS = {
    "keycloak": {
        "KEYCLOAK_URL",
        "KEYCLOAK_REALM",
        "KEYCLOAK_CLIENT_ID",
        "KEYCLOAK_CLIENT_SECRET",
        "KEYCLOAK_CLIENT_PUBLIC",
        "KEYCLOAK_VERIFY_SSL",
        "KEYCLOAK_AUDIENCE",
        "KEYCLOAK_TOKEN_GRANT_TYPE",
        "KEYCLOAK_TOKEN_SCOPE",
        "KEYCLOAK_TOKEN_USERNAME",
        "KEYCLOAK_TOKEN_PASSWORD",
        "KEYCLOAK_REQUEST_TIMEOUT_SECONDS",
        "KEYCLOAK_MAX_RETRIES",
    },
    "postgres": {
        "POSTGRES_DSN",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_SSLMODE",
        "POSTGRES_CONNECT_TIMEOUT_SECONDS",
        "POSTGRES_POOL_SIZE",
        "POSTGRES_MAX_OVERFLOW",
    },
    "minio": {
        "MINIO_ENDPOINT",
        "MINIO_ACCESS_KEY",
        "MINIO_SECRET_KEY",
        "MINIO_SECURE",
        "MINIO_REGION",
        "MINIO_BUCKET",
        "MINIO_REQUEST_TIMEOUT_SECONDS",
        "MINIO_MAX_RETRIES",
    },
    "milvus": {
        "MILVUS_URI",
        "MILVUS_TOKEN",
        "MILVUS_DB_NAME",
        "MILVUS_COLLECTION",
        "MILVUS_SECURE",
        "MILVUS_CONNECT_TIMEOUT_SECONDS",
        "MILVUS_REQUEST_TIMEOUT_SECONDS",
        "MILVUS_MAX_RETRIES",
    },
    "ollama": {
        "OLLAMA_HOST",
        "OLLAMA_GENERATION_MODEL",
        "OLLAMA_EMBEDDING_MODEL",
        "OLLAMA_REQUEST_TIMEOUT_SECONDS",
        "OLLAMA_MAX_RETRIES",
    },
    "langfuse": {
        "LANGFUSE_ENABLED",
        "LANGFUSE_HOST",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_RELEASE",
        "LANGFUSE_ENVIRONMENT",
        "LANGFUSE_REQUEST_TIMEOUT_SECONDS",
        "LANGFUSE_MAX_RETRIES",
    },
    "nats": {
        "NATS_SERVERS",
        "NATS_USER",
        "NATS_PASSWORD",
        "NATS_TOKEN",
        "NATS_CREDS_FILE",
        "NATS_NAME",
        "NATS_CONNECT_TIMEOUT_SECONDS",
        "NATS_MAX_RECONNECT_ATTEMPTS",
    },
}


REQUIRED_SERVICE_ENV_KEYS = {
    "postgres": (("POSTGRES_DSN",), ("POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD")),
    "minio": (("MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY"),),
    "milvus": (("MILVUS_URI",),),
    "ollama": (("OLLAMA_HOST",),),
    "langfuse": (("LANGFUSE_ENABLED", "LANGFUSE_HOST", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"),),
    "nats": (("NATS_SERVERS",),),
}


def _service_env(service_name: str) -> dict[str, str]:
    actual = _integration_env()
    env = _base_env()
    env.update({key: actual[key] for key in {"DOCMESH_ENV", "DOCMESH_HEALTHCHECK_ENABLED"} if actual.get(key)})
    env.update({key: actual[key] for key in SERVICE_ENV_KEYS[service_name] if actual.get(key)})
    return env


def _require_integration_environment() -> None:
    current_env = _integration_env().get("DOCMESH_ENV", "").strip().lower()
    if current_env != INTEGRATION_ENV_NAME:
        pytest.skip("Set DOCMESH_ENV=integration to run real-service integration tests")


def _service_is_configured(service_name: str) -> bool:
    env = _integration_env()
    if service_name == "langfuse" and env.get("LANGFUSE_ENABLED", "true").lower() == "false":
        return False
    requirement_groups = REQUIRED_SERVICE_ENV_KEYS[service_name]
    return any(all(env.get(key) for key in group) for group in requirement_groups)


def _keycloak_discovery_is_configured() -> bool:
    env = _integration_env()
    return bool(env.get("KEYCLOAK_URL") and env.get("KEYCLOAK_REALM"))


def _keycloak_token_is_configured() -> bool:
    env = _integration_env()
    if not _keycloak_discovery_is_configured() or not env.get("KEYCLOAK_CLIENT_ID"):
        return False
    grant_type = env.get("KEYCLOAK_TOKEN_GRANT_TYPE", "client_credentials")
    if grant_type == "password":
        return bool(env.get("KEYCLOAK_TOKEN_USERNAME") and env.get("KEYCLOAK_TOKEN_PASSWORD"))
    return bool(env.get("KEYCLOAK_CLIENT_SECRET"))


@pytest.mark.keycloak
def test_keycloak_oidc_discovery_endpoint_is_reachable():
    _require_integration_environment()
    if not _keycloak_discovery_is_configured():
        pytest.skip("KEYCLOAK_URL/KEYCLOAK_REALM not configured for integration testing")

    env = _integration_env()
    issuer = f"{env['KEYCLOAK_URL'].rstrip('/')}/realms/{env['KEYCLOAK_REALM']}"
    discovery_url = f"{issuer}/.well-known/openid-configuration"

    with urlopen(discovery_url, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))

    assert payload["issuer"] == issuer
    assert payload["token_endpoint"].startswith(issuer)
    assert payload["jwks_uri"].startswith(issuer)


@pytest.mark.keycloak
def test_keycloak_fetch_access_token_against_real_service():
    _require_integration_environment()
    if not _keycloak_token_is_configured():
        pytest.skip("Keycloak token grant settings are incomplete for integration testing")

    settings = load_settings(_service_env("keycloak"))

    token = KeycloakAuthService(settings).fetch_access_token()

    assert token.access_token
    assert token.token_type
    assert token.expires_in > 0


@pytest.mark.health
def test_postgres_wrapper_check_against_real_service():
    _require_integration_environment()
    if not _service_is_configured("postgres"):
        pytest.skip("PostgreSQL integration settings are not configured")

    settings = load_settings(_service_env("postgres"))
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
    _require_integration_environment()
    if not _service_is_configured("minio"):
        pytest.skip("MinIO integration settings are not configured")

    settings = load_settings(_service_env("minio"))
    client = ServiceFactoryRegistry(settings).create_client("minio")

    buckets = client.check()

    assert buckets is not None


@pytest.mark.health
def test_milvus_wrapper_check_against_real_service():
    _require_integration_environment()
    if not _service_is_configured("milvus"):
        pytest.skip("Milvus integration settings are not configured")

    settings = load_settings(_service_env("milvus"))
    client = ServiceFactoryRegistry(settings).create_client("milvus")

    collections = client.check()

    assert collections is not None


@pytest.mark.health
def test_ollama_wrapper_check_against_real_service():
    _require_integration_environment()
    if not _service_is_configured("ollama"):
        pytest.skip("Ollama integration settings are not configured")

    settings = load_settings(_service_env("ollama"))
    client = ServiceFactoryRegistry(settings).create_client("ollama")

    response = client.check()

    assert response is not None


@pytest.mark.health
def test_langfuse_wrapper_check_against_real_service():
    _require_integration_environment()
    if not _service_is_configured("langfuse"):
        pytest.skip("Langfuse integration settings are not configured or disabled")

    settings = load_settings(_service_env("langfuse"))
    client = ServiceFactoryRegistry(settings).create_client("langfuse")

    result = client.check()

    assert result is not None


@pytest.mark.health
def test_nats_builder_check_against_real_service():
    _require_integration_environment()
    if not _service_is_configured("nats"):
        pytest.skip("NATS integration settings are not configured")

    settings = load_settings(_service_env("nats"))
    builder = ServiceFactoryRegistry(settings).create_client("nats")

    result = asyncio.run(builder.check())

    assert result is not None
