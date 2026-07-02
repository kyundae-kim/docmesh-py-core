from __future__ import annotations

from contextlib import contextmanager
import os
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

INTEGRATION_ENV_NAME = "integration"
DOCMESH_ENV_PREFIXES = (
    "DOCMESH_",
    "KEYCLOAK_",
    "POSTGRES_",
    "SQLITE_",
    "MINIO_",
    "MILVUS_",
    "OLLAMA_",
    "LANGFUSE_",
    "NATS_",
)
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
    "sqlite": (("SQLITE_PATH",),),
    "minio": (("MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY"),),
    "milvus": (("MILVUS_URI",),),
    "ollama": (("OLLAMA_HOST",),),
    "langfuse": (("LANGFUSE_ENABLED", "LANGFUSE_HOST", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"),),
    "nats": (("NATS_SERVERS",),),
}


def parse_env_file(path: Path) -> dict[str, str]:
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
        if value and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        parsed[key] = value
    return parsed

from docmesh_py_core.config import ServiceConfigs, load_service_configs


def _stringify_env_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    return str(value)


def integration_env() -> ServiceConfigs:
    env = base_integration_env()
    env.update(parse_env_file(ROOT / 'env' / 'integration.env'))
    with pytest.MonkeyPatch.context() as monkeypatch:
        apply_docmesh_env(monkeypatch, env)
        return load_service_configs()


from docmesh_py_core.config import KeycloakConfig, KeycloakDiscoveryConfig
from pydantic_settings import SettingsConfigDict


class KeycloakIntegrationDiscoveryConfig(KeycloakDiscoveryConfig):
    model_config = SettingsConfigDict(case_sensitive=False, env_prefix='KEYCLOAK_', env_file='env/integration.env')


class KeycloakIntegrationConfig(KeycloakConfig):
    model_config = SettingsConfigDict(case_sensitive=False, env_prefix='KEYCLOAK_', env_file='env/integration.env')


def base_integration_env() -> dict[str, str]:
    return {
        "DOCMESH_ENV": INTEGRATION_ENV_NAME,
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
        "SQLITE_PATH": ":memory:",
        "MINIO_ENDPOINT": "localhost:9000",
        "MINIO_ACCESS_KEY": "placeholder-access-key",
        "MINIO_SECRET_KEY": "placeholder-secret-key",
        "MINIO_SECURE": "false",
        "MILVUS_URI": "http://localhost:19530",
        "OLLAMA_HOST": "http://localhost:11434",
        "LANGFUSE_ENABLED": "false",
        "NATS_SERVERS": "nats://localhost:4222",
    }


def service_env(service_name: str) -> dict[str, str]:
    settings = integration_env()
    env = base_integration_env()
    env["DOCMESH_ENV"] = _stringify_env_value(settings.common.env)
    env["DOCMESH_HEALTHCHECK_ENABLED"] = _stringify_env_value(settings.common.healthcheck_enabled)

    service_settings = getattr(settings, service_name)
    if service_settings is None:
        return env

    service_settings_cls = type(service_settings)
    for field_name in service_settings_cls.model_fields:
        value = getattr(service_settings, field_name)
        if value is None:
            continue
        env_key = service_settings_cls.env_key(field_name)
        env[env_key] = _stringify_env_value(value)
    return env


def apply_docmesh_env(monkeypatch: pytest.MonkeyPatch, env: dict[str, str]) -> None:
    for env_key in tuple(os.environ):
        if env_key.startswith(DOCMESH_ENV_PREFIXES):
            monkeypatch.delenv(env_key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, _stringify_env_value(value))


@contextmanager
def docmesh_env_context(env: dict[str, str]):
    with pytest.MonkeyPatch.context() as monkeypatch:
        apply_docmesh_env(monkeypatch, env)
        yield env


def activate_service_env(monkeypatch: pytest.MonkeyPatch, service_name: str) -> dict[str, str]:
    env = service_env(service_name)
    apply_docmesh_env(monkeypatch, env)
    return env


@contextmanager
def activated_service_env(service_name: str):
    env = service_env(service_name)
    with docmesh_env_context(env):
        yield env


def require_integration_environment() -> None:
    current_env = str(integration_env().common.env).strip().lower()
    if current_env != INTEGRATION_ENV_NAME:
        pytest.skip("Set DOCMESH_ENV=integration to run real-service integration tests")


def service_is_configured(service_name: str) -> bool:
    settings = integration_env()
    service_settings = getattr(settings, service_name)
    if service_settings is None:
        return False
    if service_name == "langfuse" and not service_settings.enabled:
        return False
    env = service_env(service_name)
    requirement_groups = REQUIRED_SERVICE_ENV_KEYS[service_name]
    return any(all(env.get(key) for key in group) for group in requirement_groups)


def keycloak_discovery_is_configured() -> bool:
    try:
        keycloak = KeycloakIntegrationDiscoveryConfig()
    except ValidationError:
        return False
    return bool(keycloak.url and keycloak.realm)


def keycloak_token_is_configured() -> bool:
    keycloak = integration_env().keycloak
    if not keycloak_discovery_is_configured() or not keycloak or not keycloak.client_id:
        return False
    grant_type = keycloak.token_grant_type
    if grant_type == "password":
        return bool(keycloak.token_username and keycloak.token_password)
    return bool(keycloak.client_secret)


@pytest.fixture(autouse=True)
def clear_docmesh_environment_for_unit_tests(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    if request.node.get_closest_marker("integration"):
        return
    for env_key in tuple(os.environ):
        if env_key.startswith(DOCMESH_ENV_PREFIXES):
            monkeypatch.delenv(env_key, raising=False)
