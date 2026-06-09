from __future__ import annotations

from unittest.mock import Mock

from docmesh_py_core.config import load_settings
from docmesh_py_core.factories import ServiceFactoryRegistry


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
