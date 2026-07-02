from __future__ import annotations

import inspect
import docmesh_py_core as package_root
import pytest

from pydantic import ValidationError
from pydantic_settings import BaseSettings


pytestmark = [pytest.mark.unit]

from docmesh_py_core.config import (
    CommonConfig,
    ConfigError,
    KeycloakDiscoveryConfig,
    KeycloakConfig,
    LangfuseConfig,
    MinioConfig,
    MilvusConfig,
    NatsConfig,
    OllamaConfig,
    PostgresConfig,
    ServiceConfigs,
    SqliteConfig,
    load_service_configs as _runtime_load_service_configs,
    validate_runtime_security,
)
from docmesh_py_core.security import mask_sensitive_value
from test_docmesh_py_core.conftest import apply_docmesh_env, keycloak_token_is_configured


def build_common_config(env: dict[str, str] | None = None) -> CommonConfig:
    with pytest.MonkeyPatch.context() as monkeypatch:
        apply_docmesh_env(monkeypatch, env or {})
        return CommonConfig()


def build_postgres_config(env: dict[str, str] | None = None):
    with pytest.MonkeyPatch.context() as monkeypatch:
        apply_docmesh_env(monkeypatch, env or {})
        return PostgresConfig()


def build_keycloak_config(env: dict[str, str] | None = None):
    with pytest.MonkeyPatch.context() as monkeypatch:
        apply_docmesh_env(monkeypatch, env or {})
        return KeycloakConfig()


def build_keycloak_discovery_config(env: dict[str, str] | None = None):
    with pytest.MonkeyPatch.context() as monkeypatch:
        apply_docmesh_env(monkeypatch, env or {})
        return KeycloakDiscoveryConfig()


def build_langfuse_config(env: dict[str, str] | None = None):
    with pytest.MonkeyPatch.context() as monkeypatch:
        apply_docmesh_env(monkeypatch, env or {})
        return LangfuseConfig()


def load_service_configs(env: dict[str, str] | None = None, *, services: set[str] | None = None):
    with pytest.MonkeyPatch.context() as monkeypatch:
        apply_docmesh_env(monkeypatch, env or {})
        return _runtime_load_service_configs(services=services)


def test_common_config_defaults():
    config = build_common_config({})

    assert isinstance(config, CommonConfig)
    assert config.env == "development"
    assert config.healthcheck_enabled is True


def test_postgres_config_raises_when_required_env_is_missing():
    with pytest.raises(ConfigError) as exc_info:
        load_service_configs({}, services={"postgres"})

    assert "POSTGRES_HOST" in str(exc_info.value)


def test_direct_postgres_config_construction_reads_process_environment():
    config = build_postgres_config({"POSTGRES_DSN": "postgresql://user:***@db.example.com:5432/app"})

    assert config.dsn == "postgresql://user:***@db.example.com:5432/app"
    assert config.port == 5432


def test_sqlite_config_raises_when_required_env_is_missing():
    with pytest.raises(ConfigError) as exc_info:
        load_service_configs({}, services={"sqlite"})

    assert "SQLITE_PATH" in str(exc_info.value)


def test_direct_keycloak_config_raises_validation_error_when_missing_required_env():
    with pytest.raises(ValidationError) as exc_info:
        build_keycloak_config({})

    assert "url" in str(exc_info.value)


def test_direct_keycloak_discovery_config_reads_process_environment_without_client_credentials():
    config = build_keycloak_discovery_config(
        {
            "KEYCLOAK_URL": "https://kc.example.com",
            "KEYCLOAK_REALM": "docmesh",
        }
    )

    assert config.url == "https://kc.example.com"
    assert config.realm == "docmesh"


def test_keycloak_config_extends_keycloak_discovery_config():
    assert issubclass(KeycloakConfig, KeycloakDiscoveryConfig)


def test_keycloak_token_configuration_helper_uses_integration_keycloak_config():
    helper_source = inspect.getsource(keycloak_token_is_configured)

    assert "KeycloakIntegrationConfig" in helper_source
    assert "integration_env().keycloak" not in helper_source


def test_keycloak_integration_services_use_integration_specific_config_models():
    source = (package_root.__path__[0] + "/../test_docmesh_py_core/test_integration_services.py")
    content = open(source, encoding="utf-8").read()

    assert "KeycloakIntegrationDiscoveryConfig()" in content
    assert "KeycloakIntegrationConfig()" in content
    assert "keycloak = KeycloakConfig()" not in content


def test_direct_basesettings_construction_reads_process_environment(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("KEYCLOAK_URL", "https://ambient.example.com")
    monkeypatch.setenv("KEYCLOAK_REALM", "ambient")
    monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "ambient-client")
    monkeypatch.setenv("KEYCLOAK_CLIENT_SECRET", "ambient-secret")

    config = KeycloakConfig()

    assert config.url == "https://ambient.example.com"
    assert config.realm == "ambient"
    assert config.client_id == "ambient-client"


def test_direct_config_construction_reads_process_environment(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("KEYCLOAK_URL", "https://ambient.example.com")
    monkeypatch.setenv("KEYCLOAK_REALM", "ambient")
    monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "ambient-client")
    monkeypatch.setenv("KEYCLOAK_CLIENT_SECRET", "ambient-secret")

    config = KeycloakConfig()

    assert config.url == "https://ambient.example.com"
    assert config.realm == "ambient"
    assert config.client_id == "ambient-client"


def test_langfuse_config_inherits_docmesh_env_when_environment_is_unset():
    config = build_langfuse_config(
        {
            "DOCMESH_ENV": "integration",
            "LANGFUSE_HOST": "https://langfuse.example.com",
            "LANGFUSE_PUBLIC_KEY": "public-key",
            "LANGFUSE_SECRET_KEY": "secret-key",
        }
    )
    assert config.environment == "integration"


def test_langfuse_config_raises_when_required_env_is_missing():
    with pytest.raises(ConfigError) as exc_info:
        load_service_configs({}, services={"langfuse"})

    assert "LANGFUSE_HOST" in str(exc_info.value)


def test_langfuse_config_defaults_environment_to_development():
    config = build_langfuse_config({"LANGFUSE_ENABLED": "false"})

    assert config.environment == "development"


def test_package_root_does_not_export_removed_config_helpers():
    assert "KeycloakDiscoveryConfig" in package_root.__all__
    assert "load_common_config" not in package_root.__all__
    assert "load_settings" not in package_root.__all__
    assert "require_keycloak_config" not in package_root.__all__
    assert "require_langfuse_config" not in package_root.__all__
    assert "require_minio_config" not in package_root.__all__
    assert "require_milvus_config" not in package_root.__all__
    assert "require_ollama_config" not in package_root.__all__
    assert "require_nats_config" not in package_root.__all__


def test_validate_runtime_security_rejects_disabled_ssl_in_production():
    common = CommonConfig(env="production")
    keycloak = KeycloakConfig(
        _env_prefix="__DOCMESH_DISABLED__",
        url="https://kc.example.com",
        realm="docmesh",
        client_id="backend",
        client_secret="secret",
        verify_ssl=False,
    )

    with pytest.raises(ConfigError) as exc_info:
        validate_runtime_security(common, keycloak=keycloak)

    assert "SSL verification" in str(exc_info.value)


def test_load_settings_parses_required_services_and_defaults():
    settings = load_service_configs(
        {
            "KEYCLOAK_URL": "https://kc.example.com",
            "KEYCLOAK_REALM": "docmesh",
            "KEYCLOAK_CLIENT_ID": "backend",
            "KEYCLOAK_CLIENT_SECRET": "client-secret",
            "POSTGRES_DSN": "postgresql://user:***@db.example.com:5432/app",
            "SQLITE_PATH": ":memory:",
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
        load_service_configs(
            {
                "KEYCLOAK_URL": "   ",
                "KEYCLOAK_REALM": "docmesh",
                "KEYCLOAK_CLIENT_ID": "backend",
                "KEYCLOAK_CLIENT_SECRET": "client-secret",
                "POSTGRES_DSN": "postgresql://user:secret@db.example.com:5432/app",
                "SQLITE_PATH": ":memory:",
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
        load_service_configs(
            {
                "KEYCLOAK_URL": "https://kc.example.com",
                "KEYCLOAK_REALM": "docmesh",
                "KEYCLOAK_CLIENT_ID": "backend",
                "KEYCLOAK_CLIENT_SECRET": "client-secret",
                "KEYCLOAK_VERIFY_SSL": "yes",
                "POSTGRES_DSN": "postgresql://user:secret@db.example.com:5432/app",
                "SQLITE_PATH": ":memory:",
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
        load_service_configs(
            {
                "KEYCLOAK_URL": "https://kc.example.com",
                "KEYCLOAK_REALM": "docmesh",
                "KEYCLOAK_CLIENT_ID": "backend",
                "KEYCLOAK_CLIENT_SECRET": "client-secret",
                "POSTGRES_DSN": "postgresql://user:secret@db.example.com:5432/app",
                "SQLITE_PATH": ":memory:",
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


def test_keycloak_confidential_client_requires_client_secret():
    with pytest.raises(ConfigError) as exc_info:
        load_service_configs(
            {
                "KEYCLOAK_URL": "https://kc.example.com",
                "KEYCLOAK_REALM": "docmesh",
                "KEYCLOAK_CLIENT_ID": "backend",
                "POSTGRES_DSN": "postgresql://user:***@db.example.com:5432/app",
                "SQLITE_PATH": ":memory:",
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

    assert "KEYCLOAK_CLIENT_SECRET" in str(exc_info.value)


def test_keycloak_public_client_allows_missing_client_secret():
    settings = load_service_configs(
        {
            "KEYCLOAK_URL": "https://kc.example.com",
            "KEYCLOAK_REALM": "docmesh",
            "KEYCLOAK_CLIENT_ID": "backend",
            "KEYCLOAK_CLIENT_PUBLIC": "true",
            "POSTGRES_DSN": "postgresql://user:***@db.example.com:5432/app",
            "SQLITE_PATH": ":memory:",
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

    assert settings.keycloak.client_public is True
    assert settings.keycloak.client_secret is None


def test_keycloak_password_grant_does_not_require_username_and_password_at_settings_load_time():
    settings = load_service_configs(
        {
            "KEYCLOAK_URL": "https://kc.example.com",
            "KEYCLOAK_REALM": "docmesh",
            "KEYCLOAK_CLIENT_ID": "backend",
            "KEYCLOAK_CLIENT_SECRET": "client-secret",
            "KEYCLOAK_TOKEN_GRANT_TYPE": "password",
            "POSTGRES_DSN": "postgresql://user:***@db.example.com:5432/app",
            "SQLITE_PATH": ":memory:",
            "MINIO_ENDPOINT": "minio.example.com:9000",
            "MINIO_ACCESS_KEY": "minio-access",
            "MINIO_SECRET_KEY": "minio-secret",
            "MILVUS_URI": "http://milvus.example.com:19530",
            "OLLAMA_HOST": "http://ollama.example.com:11434",
            "LANGFUSE_ENABLED": "false",
            "NATS_SERVERS": "nats://n1:4222",
        }
    )

    assert settings.keycloak.token_grant_type == "password"
    assert settings.keycloak.token_username is None
    assert settings.keycloak.token_password is None


def test_keycloak_provisioning_requires_single_admin_auth_mode():
    with pytest.raises(ConfigError) as exc_info:
        load_service_configs(
            {
                "KEYCLOAK_URL": "https://kc.example.com",
                "KEYCLOAK_REALM": "docmesh",
                "KEYCLOAK_CLIENT_ID": "backend",
                "KEYCLOAK_CLIENT_SECRET": "client-secret",
                "KEYCLOAK_PROVISIONING_ENABLED": "true",
                "KEYCLOAK_ADMIN_CLIENT_SECRET": "secret",
                "KEYCLOAK_ADMIN_USERNAME": "admin",
                "KEYCLOAK_ADMIN_PASSWORD": "password",
                "POSTGRES_DSN": "postgresql://user:secret@db.example.com:5432/app",
                "SQLITE_PATH": ":memory:",
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
    settings = load_service_configs(
        {
            "KEYCLOAK_URL": "https://kc.example.com",
            "KEYCLOAK_REALM": "docmesh",
            "KEYCLOAK_CLIENT_ID": "backend",
            "KEYCLOAK_CLIENT_SECRET": "client-secret",
            "POSTGRES_DSN": "postgresql://user:***@db.example.com:5432/app",
            "SQLITE_PATH": ":memory:",
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


def test_load_settings_supports_sqlite_without_postgres_configuration():
    settings = load_service_configs(
        {
            "KEYCLOAK_URL": "https://kc.example.com",
            "KEYCLOAK_REALM": "docmesh",
            "KEYCLOAK_CLIENT_ID": "backend",
            "KEYCLOAK_CLIENT_SECRET": "client-secret",
            "SQLITE_PATH": ":memory:",
            "MINIO_ENDPOINT": "minio.example.com:9000",
            "MINIO_ACCESS_KEY": "minio-access",
            "MINIO_SECRET_KEY": "minio-secret",
            "MILVUS_URI": "http://milvus.example.com:19530",
            "OLLAMA_HOST": "http://ollama.example.com:11434",
            "LANGFUSE_ENABLED": "false",
            "NATS_SERVERS": "nats://n1:4222",
        },
        services={"sqlite"},
    )

    assert settings.postgres is None
    assert isinstance(settings.sqlite, SqliteConfig)
    assert settings.sqlite.path == ":memory:"
    assert settings.sqlite.readonly is False
    assert settings.sqlite.enable_wal is False
    assert settings.sqlite.busy_timeout_ms == 5000


def test_load_settings_can_limit_validation_to_selected_services():
    settings = load_service_configs(
        {
            "DOCMESH_ENV": "integration",
            "NATS_SERVERS": "nats://n1:4222",
        },
        services={"nats"},
    )

    assert settings.common.env == "integration"
    assert settings.nats is not None
    assert settings.nats.servers == ["nats://n1:4222"]
    assert settings.keycloak is None
    assert settings.postgres is None
    assert settings.sqlite is None
    assert settings.minio is None
    assert settings.milvus is None
    assert settings.ollama is None
    assert settings.langfuse is None


def test_load_settings_skips_cross_service_defaults_for_unselected_services():
    settings = load_service_configs(
        {
            "DOCMESH_ENV": "production",
            "LANGFUSE_ENABLED": "false",
        },
        services={"langfuse"},
    )

    assert settings.common.env == "production"
    assert settings.langfuse is not None
    assert settings.langfuse.enabled is False
    assert settings.langfuse.environment == "production"
    assert settings.keycloak is None


def test_load_settings_parses_sqlite_boolean_and_range_fields():
    settings = load_service_configs(
        {
            "KEYCLOAK_URL": "https://kc.example.com",
            "KEYCLOAK_REALM": "docmesh",
            "KEYCLOAK_CLIENT_ID": "backend",
            "KEYCLOAK_CLIENT_SECRET": "client-secret",
            "SQLITE_PATH": "./var/app.db",
            "SQLITE_READONLY": "true",
            "SQLITE_ENABLE_WAL": "true",
            "SQLITE_BUSY_TIMEOUT_MS": "2500",
            "MINIO_ENDPOINT": "minio.example.com:9000",
            "MINIO_ACCESS_KEY": "minio-access",
            "MINIO_SECRET_KEY": "minio-secret",
            "MILVUS_URI": "http://milvus.example.com:19530",
            "OLLAMA_HOST": "http://ollama.example.com:11434",
            "LANGFUSE_ENABLED": "false",
            "NATS_SERVERS": "nats://n1:4222",
        },
        services={"sqlite"},
    )

    assert settings.sqlite is not None
    assert settings.sqlite.readonly is True
    assert settings.sqlite.enable_wal is True
    assert settings.sqlite.busy_timeout_ms == 2500


def test_load_settings_rejects_invalid_sqlite_values():
    with pytest.raises(ConfigError) as exc_info:
        load_service_configs(
            {
                "KEYCLOAK_URL": "https://kc.example.com",
                "KEYCLOAK_REALM": "docmesh",
                "KEYCLOAK_CLIENT_ID": "backend",
                "KEYCLOAK_CLIENT_SECRET": "client-secret",
                "SQLITE_PATH": "./var/app.db",
                "SQLITE_READONLY": "yes",
                "MINIO_ENDPOINT": "minio.example.com:9000",
                "MINIO_ACCESS_KEY": "minio-access",
                "MINIO_SECRET_KEY": "minio-secret",
                "MILVUS_URI": "http://milvus.example.com:19530",
                "OLLAMA_HOST": "http://ollama.example.com:11434",
                "LANGFUSE_ENABLED": "false",
                "NATS_SERVERS": "nats://n1:4222",
            },
            services={"sqlite"},
        )

    assert "SQLITE_READONLY" in str(exc_info.value)

    with pytest.raises(ConfigError) as range_exc_info:
        load_service_configs(
            {
                "KEYCLOAK_URL": "https://kc.example.com",
                "KEYCLOAK_REALM": "docmesh",
                "KEYCLOAK_CLIENT_ID": "backend",
                "KEYCLOAK_CLIENT_SECRET": "client-secret",
                "SQLITE_PATH": "./var/app.db",
                "SQLITE_BUSY_TIMEOUT_MS": "-1",
                "MINIO_ENDPOINT": "minio.example.com:9000",
                "MINIO_ACCESS_KEY": "minio-access",
                "MINIO_SECRET_KEY": "minio-secret",
                "MILVUS_URI": "http://milvus.example.com:19530",
                "OLLAMA_HOST": "http://ollama.example.com:11434",
                "LANGFUSE_ENABLED": "false",
                "NATS_SERVERS": "nats://n1:4222",
            },
            services={"sqlite"},
        )

    assert "SQLITE_BUSY_TIMEOUT_MS" in str(range_exc_info.value)


def test_nats_allows_only_single_authentication_mode():
    with pytest.raises(ConfigError) as exc_info:
        load_service_configs(
            {
                "KEYCLOAK_URL": "https://kc.example.com",
                "KEYCLOAK_REALM": "docmesh",
                "KEYCLOAK_CLIENT_ID": "backend",
                "KEYCLOAK_CLIENT_SECRET": "client-secret",
                "POSTGRES_DSN": "postgresql://user:secret@db.example.com:5432/app",
                "SQLITE_PATH": ":memory:",
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
        load_service_configs(
            {
                "DOCMESH_ENV": "production",
                "KEYCLOAK_URL": "https://kc.example.com",
                "KEYCLOAK_REALM": "docmesh",
                "KEYCLOAK_CLIENT_ID": "backend",
                "KEYCLOAK_CLIENT_SECRET": "client-secret",
                "KEYCLOAK_VERIFY_SSL": "false",
                "POSTGRES_DSN": "postgresql://user:secret@db.example.com:5432/app",
                "SQLITE_PATH": ":memory:",
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
    assert issubclass(SqliteConfig, BaseSettings)
    assert issubclass(LangfuseConfig, BaseSettings)
    assert issubclass(NatsConfig, BaseSettings)


def test_service_configs_use_settings_config_prefixes_instead_of_validation_aliases(monkeypatch: pytest.MonkeyPatch):
    assert KeycloakConfig.model_config.get("env_prefix") == "KEYCLOAK_"
    assert PostgresConfig.model_config.get("env_prefix") == "POSTGRES_"
    assert SqliteConfig.model_config.get("env_prefix") == "SQLITE_"
    assert LangfuseConfig.model_config.get("env_prefix") == "LANGFUSE_"
    assert NatsConfig.model_config.get("env_prefix") == "NATS_"
    assert KeycloakConfig.model_fields["url"].validation_alias is None
    assert KeycloakConfig.model_fields["realm"].validation_alias is None
    assert KeycloakConfig.model_fields["client_id"].validation_alias is None

    monkeypatch.setenv("KEYCLOAK_URL", "https://kc.example.com")
    monkeypatch.setenv("KEYCLOAK_REALM", "docmesh")
    monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "backend")
    monkeypatch.setenv("KEYCLOAK_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("KEYCLOAK_CLIENT_REDIRECT_URIS", "https://app.example.com/callback, https://admin.example.com/callback")

    config = KeycloakConfig()

    assert config.url == "https://kc.example.com"
    assert config.realm == "docmesh"
    assert config.client_id == "backend"
    assert config.client_redirect_uris == [
        "https://app.example.com/callback",
        "https://admin.example.com/callback",
    ]


def test_service_configs_is_thin_bundle_and_builds_from_environment(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("DOCMESH_ENV", raising=False)

    env_values = {
        "KEYCLOAK_URL": "https://kc.example.com",
        "KEYCLOAK_REALM": "docmesh",
        "KEYCLOAK_CLIENT_ID": "backend",
        "KEYCLOAK_CLIENT_SECRET": "client-secret",
        "POSTGRES_DSN": "postgresql://user:***@db.example.com:5432/app",
        "SQLITE_PATH": ":memory:",
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

    settings = load_service_configs(env_values)

    assert isinstance(settings, ServiceConfigs)
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
