from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from docmesh_py_core.config import load_settings
from docmesh_py_core.pagination import Page
from docmesh_py_core.serialization import to_serializable
from docmesh_py_core.snapshot import build_settings_snapshot


pytestmark = [pytest.mark.unit]


@dataclass
class _Item:
    name: str
    created_at: datetime


def _settings():
    return load_settings(
        {
            "KEYCLOAK_URL": "https://kc.example.com",
            "KEYCLOAK_REALM": "docmesh",
            "KEYCLOAK_CLIENT_ID": "backend",
            "KEYCLOAK_CLIENT_SECRET": "client-secret",
            "POSTGRES_DSN": "postgresql://user:secret-pass@db.example.com:5432/app?password=hunter2",
            "MINIO_ENDPOINT": "minio.example.com:9000",
            "MINIO_ACCESS_KEY": "minio-access",
            "MINIO_SECRET_KEY": "minio-secret",
            "MILVUS_URI": "http://milvus.example.com:19530",
            "OLLAMA_HOST": "http://ollama.example.com:11434",
            "LANGFUSE_ENABLED": "false",
            "NATS_SERVERS": "nats://token-secret@n1:4222",
        }
    )


def test_to_serializable_normalizes_dataclasses_datetimes_and_pydantic_models():
    item = _Item(name="docmesh", created_at=datetime(2026, 6, 19, 12, 30, tzinfo=UTC))
    settings = _settings()

    serialized = to_serializable(
        {
            "item": item,
            "settings": settings,
            "tags": {"sdk", "core"},
        }
    )

    assert serialized["item"] == {
        "name": "docmesh",
        "created_at": "2026-06-19T12:30:00+00:00",
    }
    assert serialized["settings"]["common"]["env"] == "development"
    assert sorted(serialized["tags"]) == ["core", "sdk"]


def test_page_builds_standard_pagination_metadata_and_items():
    page = Page.from_items(
        items=[{"id": 1}, {"id": 2}],
        total=5,
        page=2,
        page_size=2,
    )

    assert page.items == [{"id": 1}, {"id": 2}]
    assert page.total == 5
    assert page.page == 2
    assert page.page_size == 2
    assert page.total_pages == 3
    assert page.has_next is True
    assert page.has_previous is True


def test_page_rejects_out_of_range_page_requests():
    with pytest.raises(ValueError) as exc_info:
        Page.from_items(items=[], total=5, page=4, page_size=2)

    assert "page" in str(exc_info.value)


def test_build_settings_snapshot_masks_sensitive_values_recursively():
    snapshot = build_settings_snapshot(_settings())

    assert snapshot["keycloak"]["client_secret"] == "***"
    assert "hunter2" not in snapshot["postgres"]["dsn"]
    assert "***" in snapshot["postgres"]["dsn"]
    assert snapshot["minio"]["secret_key"] == "***"
    assert "token-secret" not in snapshot["nats"]["servers"][0]
    assert "***" in snapshot["nats"]["servers"][0]
    assert snapshot["langfuse"]["enabled"] is False
