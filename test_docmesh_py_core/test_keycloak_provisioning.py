from __future__ import annotations

from unittest.mock import Mock

import pytest

from docmesh_py_core.config import load_settings
from docmesh_py_core.keycloak import KeycloakProvisioner


pytestmark = [pytest.mark.keycloak]


def _settings(*, dry_run: bool = False):
    return load_settings(
        {
            "KEYCLOAK_URL": "https://kc.example.com",
            "KEYCLOAK_REALM": "docmesh",
            "KEYCLOAK_CLIENT_ID": "backend",
            "KEYCLOAK_CLIENT_SECRET": "client-secret",
            "KEYCLOAK_PROVISIONING_ENABLED": "true",
            "KEYCLOAK_PROVISIONING_DRY_RUN": "true" if dry_run else "false",
            "KEYCLOAK_ADMIN_CLIENT_SECRET": "admin-secret",
            "POSTGRES_DSN": "postgresql://user:***@db.example.com:5432/app",
            "MINIO_ENDPOINT": "minio.example.com:9000",
            "MINIO_ACCESS_KEY": "minio-access",
            "MINIO_SECRET_KEY": "minio-secret",
            "MILVUS_URI": "http://milvus.example.com:19530",
            "OLLAMA_HOST": "http://ollama.example.com:11434",
            "LANGFUSE_HOST": "https://langfuse.example.com",
            "LANGFUSE_PUBLIC_KEY": "public-key",
            "LANGFUSE_SECRET_KEY": "secret-key",
            "NATS_SERVERS": "nats://n1:4222",
            "KEYCLOAK_REALM_ROLES": "reader,writer",
            "KEYCLOAK_CLIENT_ROLES": "admin",
        }
    )


def test_keycloak_provisioner_reports_created_updated_unchanged_and_failed_items():
    admin = Mock()
    admin.ensure_realm.return_value = "created"
    admin.ensure_client.return_value = "updated"
    admin.ensure_realm_role.side_effect = ["unchanged", RuntimeError("client_secret leaked-value")]
    admin.ensure_client_role.return_value = "created"

    result = KeycloakProvisioner(_settings(), admin_client=admin).provision()

    assert result.created == ["realm:docmesh", "client-role:backend/admin"]
    assert result.updated == ["client:backend"]
    assert result.unchanged == ["realm-role:reader"]
    assert result.failed[0][0] == "realm-role:writer"
    assert "leaked-value" not in result.failed[0][1]
    assert "***" in result.failed[0][1]


def test_keycloak_provisioner_supports_dry_run_without_mutations():
    admin = Mock()

    result = KeycloakProvisioner(_settings(dry_run=True), admin_client=admin).provision()

    assert result.dry_run is True
    assert "realm:docmesh" in result.planned
    assert "client:backend" in result.planned
    admin.ensure_realm.assert_not_called()
    admin.ensure_client.assert_not_called()
