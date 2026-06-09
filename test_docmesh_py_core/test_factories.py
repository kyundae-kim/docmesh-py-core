from __future__ import annotations

from unittest.mock import Mock

from docmesh_py_core.config import load_settings
from docmesh_py_core.factories import NatsConnectionBuilder, ServiceFactoryRegistry


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

    assert postgres_client is postgres_builder.return_value
    assert minio_client is minio_builder.return_value
    postgres_builder.assert_called_once_with(registry.settings.postgres)
    minio_builder.assert_called_once_with(registry.settings.minio)


def test_service_factory_registry_closes_only_clients_that_support_close():
    closable = Mock()
    closable.close = Mock()
    non_closable = object()

    registry = ServiceFactoryRegistry(
        _settings(),
        postgres_builder=Mock(return_value=closable),
        ollama_builder=Mock(return_value=non_closable),
    )

    registry.create_client("postgres")
    registry.create_client("ollama")
    registry.close_all()

    closable.close.assert_called_once_with()


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

    assert clients["keycloak"] is fake_keycloak_client
    assert clients["postgres"] is fake_postgres_client
    assert clients["minio"] is fake_minio_client
    assert clients["milvus"] is fake_milvus_client
    assert clients["ollama"] is fake_ollama_client
    assert clients["langfuse"] is fake_langfuse_client
    assert isinstance(clients["nats"], NatsConnectionBuilder)
    assert clients["nats"].servers == ["nats://n1:4222"]
    assert clients["nats"].name == "docmesh-py-core"

    keycloak_ctor.assert_called_once_with(registry.settings)
    postgres_ctor.assert_called_once_with(
        "postgresql://docmesh:secret@db.example.com:5432/app",
        pool_size=5,
        max_overflow=10,
        connect_args={"connect_timeout": 10, "sslmode": "prefer"},
    )
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
