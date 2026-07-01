from __future__ import annotations

import warnings
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.engine import URL

pytestmark = [pytest.mark.unit]

from docmesh_py_core.config import load_settings as _runtime_load_settings
from docmesh_py_core.factories import (
    NatsConnectionBuilder,
    ServiceClientWrapper,
    ServiceClientWrapperError,
    close_service_clients,
    create_keycloak_client,
    create_langfuse_client,
    create_milvus_client,
    create_minio_client,
    create_nats_client,
    create_ollama_client,
    create_postgres_client,
    create_sqlite_client,
)
from test_docmesh_py_core.conftest import apply_docmesh_env


def load_settings(env: dict[str, str] | None = None, *, services: set[str] | None = None):
    with pytest.MonkeyPatch.context() as monkeypatch:
        apply_docmesh_env(monkeypatch, env or {})
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            return _runtime_load_settings(services=services)


def _sqlite_settings():
    return load_settings(
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


def _settings():
    return load_settings(
        {
            "KEYCLOAK_URL": "https://kc.example.com",
            "KEYCLOAK_REALM": "docmesh",
            "KEYCLOAK_CLIENT_ID": "backend",
            "KEYCLOAK_CLIENT_SECRET": "client-secret",
            "POSTGRES_HOST": "db.example.com",
            "POSTGRES_DB": "app",
            "POSTGRES_USER": "docmesh",
            "POSTGRES_PASSWORD": "secret",
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


def test_service_client_wrapper_wraps_healthcheck_failures_in_standardized_error():
    broken_client = Mock(name="broken-minio-client")
    broken_client.list_buckets.side_effect = RuntimeError("password=super-secret")

    wrapped = ServiceClientWrapper(
        client=broken_client,
        service_name="minio",
        healthcheck=broken_client.list_buckets,
    )

    with pytest.raises(ServiceClientWrapperError) as exc_info:
        wrapped.check()

    assert exc_info.value.service == "minio"
    assert exc_info.value.operation == "healthcheck"
    assert exc_info.value.error_type == "runtime_error"
    assert "super-secret" not in str(exc_info.value)
    assert "***" in str(exc_info.value)


def test_close_service_clients_closes_only_clients_that_support_close():
    closable = Mock()
    closable.close = Mock()
    non_closable = object()

    close_service_clients([closable, non_closable, None])

    closable.close.assert_called_once_with()


def test_create_postgres_and_minio_clients_are_lazy_wrapped(monkeypatch):
    fake_postgres_client = Mock(name="postgres-client")
    fake_minio_client = Mock(name="minio-client")
    postgres_ctor = Mock(return_value=fake_postgres_client)
    minio_ctor = Mock(return_value=fake_minio_client)

    monkeypatch.setattr("docmesh_py_core.factories.create_engine", postgres_ctor)
    monkeypatch.setattr("docmesh_py_core.factories.Minio", minio_ctor)

    settings = _settings()
    postgres_client = create_postgres_client(settings.postgres)
    minio_client = create_minio_client(settings.minio)

    assert isinstance(postgres_client, ServiceClientWrapper)
    assert isinstance(minio_client, ServiceClientWrapper)
    assert postgres_client.client is fake_postgres_client
    assert minio_client.client is fake_minio_client
    postgres_ctor.assert_called_once()
    minio_ctor.assert_called_once_with(
        settings.minio.endpoint,
        access_key=settings.minio.access_key,
        secret_key=settings.minio.secret_key,
        secure=settings.minio.secure,
        region=settings.minio.region,
        cert_check=settings.minio.secure,
    )


def test_create_keycloak_nats_and_langfuse_clients_use_service_specific_constructors(monkeypatch):
    fake_keycloak_client = Mock(name="keycloak-client")
    fake_langfuse_client = Mock(name="langfuse-client")
    keycloak_ctor = Mock(return_value=fake_keycloak_client)
    langfuse_ctor = Mock(return_value=fake_langfuse_client)

    monkeypatch.setattr("docmesh_py_core.factories.KeycloakAuthService", keycloak_ctor)
    monkeypatch.setattr("docmesh_py_core.factories.Langfuse", langfuse_ctor)

    settings = _settings()
    keycloak_client = create_keycloak_client(settings.keycloak)
    nats_client = create_nats_client(settings.nats)
    langfuse_client = create_langfuse_client(settings.langfuse)

    assert isinstance(keycloak_client, ServiceClientWrapper)
    assert isinstance(nats_client, NatsConnectionBuilder)
    assert isinstance(langfuse_client, ServiceClientWrapper)
    assert keycloak_client.client is fake_keycloak_client
    assert langfuse_client.client is fake_langfuse_client
    keycloak_ctor.assert_called_once_with(settings.keycloak)
    assert nats_client.servers == ["nats://n1:4222"]
    assert nats_client.name == "docmesh-py-core"


def test_create_langfuse_client_returns_none_when_disabled():
    settings = load_settings(
        {
            "KEYCLOAK_URL": "https://kc.example.com",
            "KEYCLOAK_REALM": "docmesh",
            "KEYCLOAK_CLIENT_ID": "backend",
            "KEYCLOAK_CLIENT_SECRET": "client-secret",
            "LANGFUSE_ENABLED": "false",
            "NATS_SERVERS": "nats://n1:4222",
            "MINIO_ENDPOINT": "minio.example.com:9000",
            "MINIO_ACCESS_KEY": "minio-access",
            "MINIO_SECRET_KEY": "minio-secret",
            "MILVUS_URI": "http://milvus.example.com:19530",
            "OLLAMA_HOST": "http://ollama.example.com:11434",
        },
        services={"langfuse", "keycloak", "minio", "milvus", "ollama", "nats"},
    )

    assert create_langfuse_client(settings.langfuse) is None


def test_create_sqlite_client_creates_wrapper_and_healthcheck(monkeypatch):
    fake_sqlite_client = Mock(name="sqlite-engine")
    connection = Mock()
    connection.exec_driver_sql.return_value = Mock()
    connection_context = Mock()
    connection_context.__enter__ = Mock(return_value=connection)
    connection_context.__exit__ = Mock(return_value=False)
    fake_sqlite_client.connect.return_value = connection_context
    fake_sqlite_client.dispose = Mock()

    sqlite_ctor = Mock(return_value=fake_sqlite_client)
    monkeypatch.setattr("docmesh_py_core.factories.create_engine", sqlite_ctor)
    monkeypatch.setattr("docmesh_py_core.factories._configure_sqlite_engine", Mock())

    sqlite_client = create_sqlite_client(_sqlite_settings().sqlite)

    assert isinstance(sqlite_client, ServiceClientWrapper)
    assert sqlite_client.client is fake_sqlite_client
    sqlite_ctor.assert_called_once()
    sqlite_client.check()
    connection.exec_driver_sql.assert_called_once_with("SELECT 1")


def test_create_postgres_client_builds_expected_sqlalchemy_url(monkeypatch):
    postgres_ctor = Mock(return_value=Mock(name="postgres-engine"))
    monkeypatch.setattr("docmesh_py_core.factories.create_engine", postgres_ctor)

    settings = _settings()
    create_postgres_client(settings.postgres)

    postgres_url = postgres_ctor.call_args.args[0]
    assert isinstance(postgres_url, URL)
    assert postgres_url.render_as_string(hide_password=True) == "postgresql+psycopg://docmesh:***@db.example.com:5432/app"


def test_create_service_specific_default_clients(monkeypatch):
    fake_milvus_client = Mock(name="milvus-client")
    fake_ollama_client = Mock(name="ollama-client")
    milvus_ctor = Mock(return_value=fake_milvus_client)
    ollama_ctor = Mock(return_value=fake_ollama_client)

    monkeypatch.setattr("docmesh_py_core.factories.MilvusClient", milvus_ctor)
    monkeypatch.setattr("docmesh_py_core.factories.OllamaClient", ollama_ctor)

    settings = _settings()
    milvus_client = create_milvus_client(settings.milvus)
    ollama_client = create_ollama_client(settings.ollama)

    assert isinstance(milvus_client, ServiceClientWrapper)
    assert isinstance(ollama_client, ServiceClientWrapper)
    assert milvus_client.client is fake_milvus_client
    assert ollama_client.client is fake_ollama_client


@pytest.mark.asyncio
async def test_nats_connection_builder_check_uses_connect_and_flush():
    fake_connection = Mock()
    fake_connection.flush = AsyncMock()
    fake_connection.close = AsyncMock()

    builder = NatsConnectionBuilder(
        servers=["nats://n1:4222"],
        name="docmesh-py-core",
        connect_timeout_seconds=10,
        max_reconnect_attempts=5,
        _connect_fn=AsyncMock(return_value=fake_connection),
    )

    result = await builder.check()

    assert result is fake_connection
    fake_connection.flush.assert_awaited_once()
    fake_connection.close.assert_awaited_once()


def test_create_nats_client_preserves_connection_defaults():
    builder = create_nats_client(_settings().nats)

    assert builder.servers == ["nats://n1:4222"]
    assert builder.name == "docmesh-py-core"
    assert builder.connect_timeout_seconds == 10
