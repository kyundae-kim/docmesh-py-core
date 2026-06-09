from __future__ import annotations

from pathlib import Path


def test_env_example_documents_all_expected_variables_without_real_secrets():
    env_example = Path(".env.example").read_text(encoding="utf-8")

    expected_keys = [
        "DOCMESH_ENV=",
        "DOCMESH_HEALTHCHECK_ENABLED=",
        "KEYCLOAK_URL=",
        "KEYCLOAK_REALM=",
        "KEYCLOAK_CLIENT_ID=",
        "KEYCLOAK_CLIENT_SECRET=",
        "KEYCLOAK_VERIFY_SSL=",
        "KEYCLOAK_AUDIENCE=",
        "KEYCLOAK_REQUEST_TIMEOUT_SECONDS=",
        "KEYCLOAK_MAX_RETRIES=",
        "KEYCLOAK_PROVISIONING_ENABLED=",
        "KEYCLOAK_PROVISIONING_DRY_RUN=",
        "KEYCLOAK_ADMIN_REALM=",
        "KEYCLOAK_ADMIN_CLIENT_ID=",
        "KEYCLOAK_ADMIN_CLIENT_SECRET=",
        "KEYCLOAK_ADMIN_USERNAME=",
        "KEYCLOAK_ADMIN_PASSWORD=",
        "KEYCLOAK_REALM_ENABLED=",
        "KEYCLOAK_REALM_DISPLAY_NAME=",
        "KEYCLOAK_CLIENT_PUBLIC=",
        "KEYCLOAK_CLIENT_REDIRECT_URIS=",
        "KEYCLOAK_CLIENT_WEB_ORIGINS=",
        "KEYCLOAK_REALM_ROLES=",
        "KEYCLOAK_CLIENT_ROLES=",
        "POSTGRES_DSN=",
        "POSTGRES_HOST=",
        "POSTGRES_PORT=",
        "POSTGRES_DB=",
        "POSTGRES_USER=",
        "POSTGRES_PASSWORD=",
        "POSTGRES_SSLMODE=",
        "POSTGRES_CONNECT_TIMEOUT_SECONDS=",
        "POSTGRES_POOL_SIZE=",
        "POSTGRES_MAX_OVERFLOW=",
        "MINIO_ENDPOINT=",
        "MINIO_ACCESS_KEY=",
        "MINIO_SECRET_KEY=",
        "MINIO_SECURE=",
        "MINIO_REGION=",
        "MINIO_BUCKET=",
        "MINIO_REQUEST_TIMEOUT_SECONDS=",
        "MINIO_MAX_RETRIES=",
        "MILVUS_URI=",
        "MILVUS_TOKEN=",
        "MILVUS_DB_NAME=",
        "MILVUS_COLLECTION=",
        "MILVUS_SECURE=",
        "MILVUS_CONNECT_TIMEOUT_SECONDS=",
        "MILVUS_REQUEST_TIMEOUT_SECONDS=",
        "MILVUS_MAX_RETRIES=",
        "OLLAMA_HOST=",
        "OLLAMA_GENERATION_MODEL=",
        "OLLAMA_EMBEDDING_MODEL=",
        "OLLAMA_REQUEST_TIMEOUT_SECONDS=",
        "OLLAMA_MAX_RETRIES=",
        "LANGFUSE_HOST=",
        "LANGFUSE_PUBLIC_KEY=",
        "LANGFUSE_SECRET_KEY=",
        "LANGFUSE_ENABLED=",
        "LANGFUSE_RELEASE=",
        "LANGFUSE_ENVIRONMENT=",
        "LANGFUSE_REQUEST_TIMEOUT_SECONDS=",
        "LANGFUSE_MAX_RETRIES=",
        "NATS_SERVERS=",
        "NATS_USER=",
        "NATS_PASSWORD=",
        "NATS_TOKEN=",
        "NATS_CREDS_FILE=",
        "NATS_NAME=",
        "NATS_CONNECT_TIMEOUT_SECONDS=",
        "NATS_MAX_RECONNECT_ATTEMPTS=",
    ]

    for key in expected_keys:
        assert key in env_example

    forbidden_real_values = [
        "super-secret",
        "hunter2",
        "AKIA",
        "BEGIN PRIVATE KEY",
        "password123",
    ]
    for value in forbidden_real_values:
        assert value not in env_example
