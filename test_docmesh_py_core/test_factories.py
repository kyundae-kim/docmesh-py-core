from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.engine import URL


pytestmark = [pytest.mark.unit]

from docmesh_py_core.config import load_settings
from docmesh_py_core.factories import (
    NatsConnectionBuilder,
    ServiceClientWrapper,
    ServiceClientWrapperError,
    ServiceFactoryRegistry,
    UnsupportedServiceError,
)


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
        }
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


def test_service_factory_registry_wraps_healthcheck_failures_in_standardized_error():
    broken_client = Mock(name="broken-minio-client")
    broken_client.list_buckets.side_effect = RuntimeError("password=super-secret")

    registry = ServiceFactoryRegistry(
        _settings(),
        minio_builder=Mock(return_value=broken_client),
    )

    wrapped = registry.create_client("minio")

    with pytest.raises(ServiceClientWrapperError) as exc_info:
        wrapped.check()

    assert exc_info.value.service == "minio"
    assert exc_info.value.operation == "healthcheck"
    assert exc_info.value.error_type == "runtime_error"
    assert "super-secret" not in str(exc_info.value)
    assert "***" in str(exc_info.value)


def test_service_factory_registry_raises_standardized_error_for_unsupported_service_name():
    registry = ServiceFactoryRegistry(_settings())

    with pytest.raises(UnsupportedServiceError) as exc_info:
        registry.create_client("redis")

    assert exc_info.value.service == "redis"
    assert exc_info.value.operation == "create_client"
    assert exc_info.value.error_type == "unsupported_service"


def test_service_factory_registry_creates_lazy_clients_without_connecting():
    postgres_builder = Mock(return_value=Mock(name="postgres-client"))
    minio_builder = Mock(return_value=Mock(name="minio-client"))

    registry = ServiceFactoryRegistry(
        _settings(),
        postgres_builder=postgres_builder,
        minio_builder=minio_builder,
    )

    postgres_client = registry.create_client("postgres")
    minio_client = registry.create_client("minio")

    assert isinstance(postgres_client, ServiceClientWrapper)
    assert isinstance(minio_client, ServiceClientWrapper)
    assert postgres_client.client is postgres_builder.return_value
    assert minio_client.client is minio_builder.return_value
    postgres_builder.assert_called_once_with(registry.settings.postgres)
    minio_builder.assert_called_once_with(registry.settings.minio)


def test_service_factory_registry_closes_only_clients_that_support_close():
    closable = Mock()
    closable.dispose = Mock()
    non_closable = Mock()
    non_closable.ps = Mock(return_value=Mock())

    registry = ServiceFactoryRegistry(
        _settings(),
        postgres_builder=Mock(return_value=closable),
        ollama_builder=Mock(return_value=non_closable),
    )

    registry.create_client("postgres")
    registry.create_client("ollama")
    registry.close_all()

    closable.dispose.assert_called_once_with()


def test_service_factory_registry_can_create_selected_clients_only():
    keycloak_builder = Mock(return_value=Mock())
    postgres_builder = Mock(return_value=Mock())

    registry = ServiceFactoryRegistry(
        _settings(),
        keycloak_builder=keycloak_builder,
        postgres_builder=postgres_builder,
    )

    registry.create_clients(["keycloak"])

    keycloak_builder.assert_called_once()
    postgres_builder.assert_not_called()


def test_service_factory_registry_exposes_only_services_loaded_into_settings():
    settings = load_settings(
        {
            "NATS_SERVERS": "nats://n1:4222",
        },
        services={"nats"},
    )
    registry = ServiceFactoryRegistry(settings)

    assert isinstance(registry.create_client("nats"), NatsConnectionBuilder)
    with pytest.raises(UnsupportedServiceError):
        registry.create_client("keycloak")


def test_service_factory_registry_creates_sqlite_wrapper_and_healthcheck(monkeypatch):
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

    registry = ServiceFactoryRegistry(_sqlite_settings())

    sqlite_client = registry.create_client("sqlite")

    assert isinstance(sqlite_client, ServiceClientWrapper)
    assert sqlite_client.client is fake_sqlite_client
    sqlite_ctor.assert_called_once()
    sqlite_client.check()
    connection.exec_driver_sql.assert_called_once_with("SELECT 1")


def test_service_factory_registry_uses_service_specific_default_builders(monkeypatch):
    fake_keycloak_client = Mock(name="keycloak-client")
    fake_postgres_client = Mock(name="postgres-engine")
    fake_minio_client = Mock(name="minio-client")
    fake_milvus_client = Mock(name="milvus-client")
    fake_ollama_client = Mock(name="ollama-client")
    fake_langfuse_client = Mock(name="langfuse-client")

    keycloak_ctor = Mock(return_value=fake_keycloak_client)
    postgres_ctor = Mock(return_value=fake_postgres_client)
    minio_ctor = Mock(return_value=fake_minio_client)
    milvus_ctor = Mock(return_value=fake_milvus_client)
    ollama_ctor = Mock(return_value=fake_ollama_client)
    langfuse_ctor = Mock(return_value=fake_langfuse_client)

    monkeypatch.setattr("docmesh_py_core.factories.KeycloakAuthService", keycloak_ctor)
    monkeypatch.setattr("docmesh_py_core.factories.create_engine", postgres_ctor)
    monkeypatch.setattr("docmesh_py_core.factories.Minio", minio_ctor)
    monkeypatch.setattr("docmesh_py_core.factories.MilvusClient", milvus_ctor)
    monkeypatch.setattr("docmesh_py_core.factories.OllamaClient", ollama_ctor)
    monkeypatch.setattr("docmesh_py_core.factories.Langfuse", langfuse_ctor)

    registry = ServiceFactoryRegistry(_settings())

    clients = registry.create_clients(
        ["keycloak", "postgres", "minio", "milvus", "ollama", "langfuse", "nats"]
    )

    assert isinstance(clients["keycloak"], ServiceClientWrapper)
    assert isinstance(clients["postgres"], ServiceClientWrapper)
    assert isinstance(clients["minio"], ServiceClientWrapper)
    assert isinstance(clients["milvus"], ServiceClientWrapper)
    assert isinstance(clients["ollama"], ServiceClientWrapper)
    assert isinstance(clients["langfuse"], ServiceClientWrapper)
    assert isinstance(clients["nats"], NatsConnectionBuilder)

    assert clients["keycloak"].client is fake_keycloak_client
    assert clients["postgres"].client is fake_postgres_client
    assert clients["minio"].client is fake_minio_client
    assert clients["milvus"].client is fake_milvus_client
    assert clients["ollama"].client is fake_ollama_client
    assert clients["langfuse"].client is fake_langfuse_client
    assert clients["nats"].servers == ["nats://n1:4222"]
    assert clients["nats"].name == "docmesh-py-core"

    keycloak_ctor.assert_called_once_with(registry.settings)
    postgres_ctor.assert_called_once()
    postgres_url = postgres_ctor.call_args.args[0]
    assert isinstance(postgres_url, URL)
    assert postgres_url.render_as_string(hide_password=True) == "postgresql+psycopg://docmesh:***@db.example.com:5432/app"
    assert postgres_url.render_as_string(hide_password=False) == "postgresql+psycopg://docmesh:secret@db.example.com:5432/app"
    assert postgres_ctor.call_args.kwargs == {
        "pool_size": 5,
        "max_overflow": 10,
        "connect_args": {"connect_timeout": 10, "sslmode": "prefer"},
    }
    minio_ctor.assert_called_once_with(
        "minio.example.com:9000",
        access_key="minio-access",
        secret_key="minio-secret",
        secure=True,
        region=None,
        cert_check=True,
    )
    milvus_ctor.assert_called_once_with(
        uri="http://milvus.example.com:19530",
        token="",
        db_name="default",
        timeout=30,
    )
    ollama_ctor.assert_called_once_with(host="http://ollama.example.com:11434", timeout=120)
    langfuse_ctor.assert_called_once_with(
        host="https://langfuse.example.com",
        public_key="public-key",
        secret_key="secret-key",
        timeout=10,
        environment="development",
        release=None,
        tracing_enabled=True,
    )


def test_service_factory_registry_returns_noop_langfuse_when_disabled(monkeypatch):
    langfuse_ctor = Mock()
    monkeypatch.setattr("docmesh_py_core.factories.Langfuse", langfuse_ctor)

    settings = load_settings(
        {
            "KEYCLOAK_URL": "https://kc.example.com",
            "KEYCLOAK_REALM": "docmesh",
            "KEYCLOAK_CLIENT_ID": "backend",
            "KEYCLOAK_CLIENT_SECRET": "client-secret",
            "POSTGRES_HOST": "db.example.com",
            "POSTGRES_DB": "app",
            "POSTGRES_USER": "docmesh",
            "POSTGRES_PASSWORD": "secret",
            "MINIO_ENDPOINT": "minio.example.com:9000",
            "MINIO_ACCESS_KEY": "minio-access",
            "MINIO_SECRET_KEY": "minio-secret",
            "MILVUS_URI": "http://milvus.example.com:19530",
            "OLLAMA_HOST": "http://ollama.example.com:11434",
            "LANGFUSE_ENABLED": "false",
            "NATS_SERVERS": "nats://n1:4222",
        }
    )

    registry = ServiceFactoryRegistry(settings)

    assert registry.create_client("langfuse") is None
    langfuse_ctor.assert_not_called()


def test_service_client_wrappers_expose_ping_and_check_methods():
    keycloak_client = Mock()
    keycloak_client.fetch_access_token.return_value = Mock(access_token="token")

    connection = Mock()
    connection.exec_driver_sql.return_value = Mock()
    connection_context = Mock()
    connection_context.__enter__ = Mock(return_value=connection)
    connection_context.__exit__ = Mock(return_value=False)
    postgres_client = Mock()
    postgres_client.connect.return_value = connection_context

    minio_client = Mock()
    minio_client.list_buckets.return_value = []

    milvus_client = Mock()
    milvus_client.list_collections.return_value = []

    ollama_client = Mock()
    ollama_client.ps.return_value = Mock()

    langfuse_client = Mock()
    langfuse_client.auth_check.return_value = True

    registry = ServiceFactoryRegistry(
        _settings(),
        keycloak_builder=Mock(return_value=keycloak_client),
        postgres_builder=Mock(return_value=postgres_client),
        minio_builder=Mock(return_value=minio_client),
        milvus_builder=Mock(return_value=milvus_client),
        ollama_builder=Mock(return_value=ollama_client),
        langfuse_builder=Mock(return_value=langfuse_client),
    )

    assert registry.create_client("keycloak").ping().access_token == "token"
    registry.create_client("keycloak").check()
    registry.create_client("postgres").check()
    registry.create_client("minio").check()
    registry.create_client("milvus").check()
    registry.create_client("ollama").check()
    assert registry.create_client("langfuse").check() is True

    keycloak_client.fetch_access_token.assert_called()
    postgres_client.connect.assert_called_once_with()
    connection.exec_driver_sql.assert_called_once_with("SELECT 1")
    minio_client.list_buckets.assert_called_once_with()
    milvus_client.list_collections.assert_called_once_with()
    ollama_client.ps.assert_called_once_with()
    langfuse_client.auth_check.assert_called_once_with()


@pytest.mark.asyncio
async def test_nats_connection_builder_exposes_async_ping_and_check():
    nats_client = Mock()
    nats_client.flush = AsyncMock()
    nats_client.close = AsyncMock()
    connect_fn = AsyncMock(return_value=nats_client)
    builder = NatsConnectionBuilder(
        servers=["nats://n1:4222"],
        name="docmesh-py-core",
        connect_timeout_seconds=10,
        max_reconnect_attempts=10,
        _connect_fn=connect_fn,
    )

    await builder.ping()
    await builder.check()

    assert connect_fn.await_count == 2
    nats_client.flush.assert_awaited()
    nats_client.close.assert_awaited()
