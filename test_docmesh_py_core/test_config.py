from __future__ import annotations

import pytest

from pydantic_settings import BaseSettings

from docmesh_py_core.config import (
    ConfigError,
    KeycloakConfig,
    LangfuseConfig,
    NatsConfig,
    PostgresConfig,
    Settings,
    load_settings,
)
from docmesh_py_core.security import mask_sensitive_value


def test_load_settings_parses_required_services_and_defaults():
    settings = load_settings(
        {
            "KEYCLOAK_URL": "https://kc.example.com",
            "KEYCLOAK_REALM": "docmesh",
            "KEYCLOAK_CLIENT_ID": "backend",
            "POSTGRES_DSN": "postgresql://user:secret@db.example.com:5432/app",
            "MINIO_ENDPOINT": "minio.example.com:9000",
            "MINIO_ACCESS_KEY": "minio-access",
            "MINIO_SECRET_KEY": "minio-secret",
            "MILVUS_URI": "http://milvus.example.com:19530",
            "OLLAMA_HOST": "http://ollama.example.com:11434",
            "LANGFUSE_HOST": "https://langfuse.example.com",
            "LANGFUSE_PUBLIC_KEY": "public-key",
            "LANGFUSE_SECRET_KEY": "secret-key",
            "NATS_SERVERS": "nats://n1:4222, nats://n2:4222",
        }
    )

    assert settings.common.env == "development"
    assert settings.common.healthcheck_enabled is True
    assert isinstance(settings.keycloak, KeycloakConfig)
    assert settings.keycloak.verify_ssl is True
    assert isinstance(settings.postgres, PostgresConfig)
    assert settings.postgres.port == 5432
    assert settings.postgres.connect_timeout_seconds == 10
    assert settings.minio.secure is True
    assert settings.milvus.db_name == "default"
    assert settings.ollama.request_timeout_seconds == 120
    assert isinstance(settings.langfuse, LangfuseConfig)
    assert settings.langfuse.environment == "development"
    assert isinstance(settings.nats, NatsConfig)
    assert settings.nats.servers == ["nats://n1:4222", "nats://n2:4222"]


def test_load_settings_rejects_blank_required_values():
    with pytest.raises(ConfigError) as exc_info:
        load_settings(
            {
                "KEYCLOAK_URL": "   ",
                "KEYCLOAK_REALM": "docmesh",
                "KEYCLOAK_CLIENT_ID": "backend",
                "POSTGRES_DSN": "postgresql://user:secret@db.example.com:5432/app",
                "MINIO_ENDPOINT": "minio.example.com:9000",
                "MINIO_ACCESS_KEY": "minio-access",
                "MINIO_SECRET_KEY": "minio-secret",
                "MILVUS_URI": "http://milvus.example.com:19530",
                "OLLAMA_HOST": "http://ollama.example.com:11434",
                "LANGFUSE_HOST": "https://langfuse.example.com",
                "LANGFUSE_PUBLIC_KEY": "public-key",
                "LANGFUSE_SECRET_KEY": "secret-key",
                "NATS_SERVERS": "nats://n1:4222",
            }
        )

    assert "KEYCLOAK_URL" in str(exc_info.value)


def test_load_settings_rejects_invalid_booleans_and_ranges():
    with pytest.raises(ConfigError) as exc_info:
        load_settings(
            {
                "KEYCLOAK_URL": "https://kc.example.com",
                "KEYCLOAK_REALM": "docmesh",
                "KEYCLOAK_CLIENT_ID": "backend",
                "KEYCLOAK_VERIFY_SSL": "yes",
                "POSTGRES_DSN": "postgresql://user:secret@db.example.com:5432/app",
                "MINIO_ENDPOINT": "minio.example.com:9000",
                "MINIO_ACCESS_KEY": "minio-access",
                "MINIO_SECRET_KEY": "minio-secret",
                "MILVUS_URI": "http://milvus.example.com:19530",
                "OLLAMA_HOST": "http://ollama.example.com:11434",
                "LANGFUSE_HOST": "https://langfuse.example.com",
                "LANGFUSE_PUBLIC_KEY": "public-key",
                "LANGFUSE_SECRET_KEY": "secret-key",
                "NATS_SERVERS": "nats://n1:4222",
            }
        )

    assert "KEYCLOAK_VERIFY_SSL" in str(exc_info.value)

    with pytest.raises(ConfigError) as range_exc_info:
        load_settings(
            {
                "KEYCLOAK_URL": "https://kc.example.com",
                "KEYCLOAK_REALM": "docmesh",
                "KEYCLOAK_CLIENT_ID": "backend",
                "POSTGRES_DSN": "postgresql://user:secret@db.example.com:5432/app",
                "POSTGRES_POOL_SIZE": "0",
                "MINIO_ENDPOINT": "minio.example.com:9000",
                "MINIO_ACCESS_KEY": "minio-access",
                "MINIO_SECRET_KEY": "minio-secret",
                "MILVUS_URI": "http://milvus.example.com:19530",
                "OLLAMA_HOST": "http://ollama.example.com:11434",
                "LANGFUSE_HOST": "https://langfuse.example.com",
                "LANGFUSE_PUBLIC_KEY": "public-key",
                "LANGFUSE_SECRET_KEY": "secret-key",
                "NATS_SERVERS": "nats://n1:4222",
            }
        )

    assert "POSTGRES_POOL_SIZE" in str(range_exc_info.value)


def test_keycloak_provisioning_requires_single_admin_auth_mode():
    with pytest.raises(ConfigError) as exc_info:
        load_settings(
            {
                "KEYCLOAK_URL": "https://kc.example.com",
                "KEYCLOAK_REALM": "docmesh",
                "KEYCLOAK_CLIENT_ID": "backend",
                "KEYCLOAK_PROVISIONING_ENABLED": "true",
                "KEYCLOAK_ADMIN_CLIENT_SECRET": "secret",
                "KEYCLOAK_ADMIN_USERNAME": "admin",
                "KEYCLOAK_ADMIN_PASSWORD": "password",
                "POSTGRES_DSN": "postgresql://user:secret@db.example.com:5432/app",
                "MINIO_ENDPOINT": "minio.example.com:9000",
                "MINIO_ACCESS_KEY": "minio-access",
                "MINIO_SECRET_KEY": "minio-secret",
                "MILVUS_URI": "http://milvus.example.com:19530",
                "OLLAMA_HOST": "http://ollama.example.com:11434",
                "LANGFUSE_HOST": "https://langfuse.example.com",
                "LANGFUSE_PUBLIC_KEY": "public-key",
                "LANGFUSE_SECRET_KEY": "secret-key",
                "NATS_SERVERS": "nats://n1:4222",
            }
        )

    assert "KEYCLOAK" in str(exc_info.value)
    assert "single admin auth mode" in str(exc_info.value)


def test_langfuse_disabled_makes_credentials_optional():
    settings = load_settings(
        {
            "KEYCLOAK_URL": "https://kc.example.com",
            "KEYCLOAK_REALM": "docmesh",
            "KEYCLOAK_CLIENT_ID": "backend",
            "POSTGRES_DSN": "postgresql://user:secret@db.example.com:5432/app",
            "MINIO_ENDPOINT": "minio.example.com:9000",
            "MINIO_ACCESS_KEY": "minio-access",
            "MINIO_SECRET_KEY": "minio-secret",
            "MILVUS_URI": "http://milvus.example.com:19530",
            "OLLAMA_HOST": "http://ollama.example.com:11434",
            "LANGFUSE_ENABLED": "false",
            "NATS_SERVERS": "nats://n1:4222",
        }
    )

    assert settings.langfuse.enabled is False
    assert settings.langfuse.host is None
    assert settings.langfuse.secret_key is None


def test_nats_allows_only_single_authentication_mode():
    with pytest.raises(ConfigError) as exc_info:
        load_settings(
            {
                "KEYCLOAK_URL": "https://kc.example.com",
                "KEYCLOAK_REALM": "docmesh",
                "KEYCLOAK_CLIENT_ID": "backend",
                "POSTGRES_DSN": "postgresql://user:secret@db.example.com:5432/app",
                "MINIO_ENDPOINT": "minio.example.com:9000",
                "MINIO_ACCESS_KEY": "minio-access",
                "MINIO_SECRET_KEY": "minio-secret",
                "MILVUS_URI": "http://milvus.example.com:19530",
                "OLLAMA_HOST": "http://ollama.example.com:11434",
                "LANGFUSE_HOST": "https://langfuse.example.com",
                "LANGFUSE_PUBLIC_KEY": "public-key",
                "LANGFUSE_SECRET_KEY": "secret-key",
                "NATS_SERVERS": "nats://n1:4222",
                "NATS_USER": "user",
                "NATS_PASSWORD": "password",
                "NATS_TOKEN": "token",
            }
        )

    assert "NATS" in str(exc_info.value)
    assert "single authentication mode" in str(exc_info.value)


def test_ssl_verification_cannot_be_disabled_in_production():
    with pytest.raises(ConfigError) as exc_info:
        load_settings(
            {
                "DOCMESH_ENV": "production",
                "KEYCLOAK_URL": "https://kc.example.com",
                "KEYCLOAK_REALM": "docmesh",
                "KEYCLOAK_CLIENT_ID": "backend",
                "KEYCLOAK_VERIFY_SSL": "false",
                "POSTGRES_DSN": "postgresql://user:secret@db.example.com:5432/app",
                "MINIO_ENDPOINT": "minio.example.com:9000",
                "MINIO_ACCESS_KEY": "minio-access",
                "MINIO_SECRET_KEY": "minio-secret",
                "MINIO_SECURE": "false",
                "MILVUS_URI": "http://milvus.example.com:19530",
                "MILVUS_SECURE": "false",
                "OLLAMA_HOST": "http://ollama.example.com:11434",
                "LANGFUSE_HOST": "https://langfuse.example.com",
                "LANGFUSE_PUBLIC_KEY": "public-key",
                "LANGFUSE_SECRET_KEY": "secret-key",
                "NATS_SERVERS": "nats://n1:4222",
            }
        )

    assert "production" in str(exc_info.value)
    assert "SSL verification" in str(exc_info.value)


def test_config_classes_are_backed_by_pydantic_settings():
    assert issubclass(KeycloakConfig, BaseSettings)
    assert issubclass(PostgresConfig, BaseSettings)
    assert issubclass(LangfuseConfig, BaseSettings)
    assert issubclass(NatsConfig, BaseSettings)


def test_service_configs_use_settings_config_prefixes_instead_of_validation_aliases(monkeypatch: pytest.MonkeyPatch):
    assert KeycloakConfig.model_config.get("env_prefix") == "KEYCLOAK_"
    assert PostgresConfig.model_config.get("env_prefix") == "POSTGRES_"
    assert LangfuseConfig.model_config.get("env_prefix") == "LANGFUSE_"
    assert NatsConfig.model_config.get("env_prefix") == "NATS_"
    assert KeycloakConfig.model_fields["url"].validation_alias is None
    assert KeycloakConfig.model_fields["realm"].validation_alias is None
    assert KeycloakConfig.model_fields["client_id"].validation_alias is None

    monkeypatch.setenv("KEYCLOAK_URL", "https://kc.example.com")
    monkeypatch.setenv("KEYCLOAK_REALM", "docmesh")
    monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "backend")
    monkeypatch.setenv("KEYCLOAK_CLIENT_REDIRECT_URIS", "https://app.example.com/callback, https://admin.example.com/callback")

    config = KeycloakConfig()

    assert config.url == "https://kc.example.com"
    assert config.realm == "docmesh"
    assert config.client_id == "backend"
    assert config.client_redirect_uris == [
        "https://app.example.com/callback",
        "https://admin.example.com/callback",
    ]


def test_settings_is_base_settings_aggregate_and_builds_from_environment(monkeypatch: pytest.MonkeyPatch):
    assert issubclass(Settings, BaseSettings)

    env_values = {
        "KEYCLOAK_URL": "https://kc.example.com",
        "KEYCLOAK_REALM": "docmesh",
        "KEYCLOAK_CLIENT_ID": "backend",
        "POSTGRES_DSN": "postgresql://user:***@db.example.com:5432/app",
        "MINIO_ENDPOINT": "minio.example.com:9000",
        "MINIO_ACCESS_KEY": "minio-access",
        "MINIO_SECRET_KEY": "minio-secret",
        "MILVUS_URI": "http://milvus.example.com:19530",
        "OLLAMA_HOST": "http://ollama.example.com:11434",
        "LANGFUSE_HOST": "https://langfuse.example.com",
        "LANGFUSE_PUBLIC_KEY": "public-key",
        "LANGFUSE_SECRET_KEY": "secret-key",
        "NATS_SERVERS": "nats://n1:4222, nats://n2:4222",
    }
    for key, value in env_values.items():
        monkeypatch.setenv(key, value)

    settings = Settings()

    assert settings.keycloak.url == "https://kc.example.com"
    assert settings.postgres.dsn == "postgresql://user:***@db.example.com:5432/app"
    assert settings.nats.servers == ["nats://n1:4222", "nats://n2:4222"]
    assert settings.langfuse.environment == "development"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("postgresql://user:secret@db.example.com:5432/app?password=hunter2&token=abcd", "postgresql://user:***@db.example.com:5432/app?password=%2A%2A%2A&token=%2A%2A%2A"),
        ("plain-secret-value", "***"),
        ("https://api.example.com?apikey=abcdef", "https://api.example.com?apikey=%2A%2A%2A"),
    ],
)
def test_mask_sensitive_value_hides_secrets(raw: str, expected: str):
    assert mask_sensitive_value(raw) == expected
