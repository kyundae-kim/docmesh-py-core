from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class CommonConfig:
    env: str = "development"
    healthcheck_enabled: bool = True


@dataclass(frozen=True)
class KeycloakConfig:
    url: str
    realm: str
    client_id: str
    client_secret: str | None = None
    verify_ssl: bool = True
    audience: str | None = None
    request_timeout_seconds: int = 10
    max_retries: int = 3
    provisioning_enabled: bool = False
    provisioning_dry_run: bool = False
    admin_realm: str = "master"
    admin_client_id: str = "admin-cli"
    admin_client_secret: str | None = None
    admin_username: str | None = None
    admin_password: str | None = None
    realm_enabled: bool = True
    realm_display_name: str | None = None
    client_public: bool = False
    client_redirect_uris: list[str] = field(default_factory=list)
    client_web_origins: list[str] = field(default_factory=list)
    realm_roles: list[str] = field(default_factory=list)
    client_roles: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PostgresConfig:
    dsn: str | None = None
    host: str | None = None
    port: int = 5432
    db: str | None = None
    user: str | None = None
    password: str | None = None
    sslmode: str = "prefer"
    connect_timeout_seconds: int = 10
    pool_size: int = 5
    max_overflow: int = 10


@dataclass(frozen=True)
class MinioConfig:
    endpoint: str
    access_key: str
    secret_key: str
    secure: bool = True
    region: str | None = None
    bucket: str | None = None
    request_timeout_seconds: int = 30
    max_retries: int = 3


@dataclass(frozen=True)
class MilvusConfig:
    uri: str
    token: str | None = None
    db_name: str = "default"
    collection: str | None = None
    secure: bool = False
    connect_timeout_seconds: int = 10
    request_timeout_seconds: int = 30
    max_retries: int = 3


@dataclass(frozen=True)
class OllamaConfig:
    host: str
    generation_model: str | None = None
    embedding_model: str | None = None
    request_timeout_seconds: int = 120
    max_retries: int = 2


@dataclass(frozen=True)
class LangfuseConfig:
    enabled: bool = True
    host: str | None = None
    public_key: str | None = None
    secret_key: str | None = None
    release: str | None = None
    environment: str | None = None
    request_timeout_seconds: int = 10
    max_retries: int = 3


@dataclass(frozen=True)
class NatsConfig:
    servers: list[str]
    user: str | None = None
    password: str | None = None
    token: str | None = None
    creds_file: str | None = None
    name: str = "docmesh-py-core"
    connect_timeout_seconds: int = 10
    max_reconnect_attempts: int = 10


@dataclass(frozen=True)
class Settings:
    common: CommonConfig
    keycloak: KeycloakConfig
    postgres: PostgresConfig
    minio: MinioConfig
    milvus: MilvusConfig
    ollama: OllamaConfig
    langfuse: LangfuseConfig
    nats: NatsConfig


def _strip(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _get_required(env: Mapping[str, str], key: str) -> str:
    value = _strip(env.get(key))
    if value is None:
        raise ConfigError(f"Missing required environment variable: {key}")
    return value


def _parse_bool(env: Mapping[str, str], key: str, *, default: bool) -> bool:
    value = _strip(env.get(key))
    if value is None:
        return default
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    raise ConfigError(f"{key} must be 'true' or 'false'")


def _parse_int(
    env: Mapping[str, str],
    key: str,
    *,
    default: int,
    minimum: int | None = None,
) -> int:
    value = _strip(env.get(key))
    if value is None:
        result = default
    else:
        try:
            result = int(value)
        except ValueError as exc:
            raise ConfigError(f"{key} must be an integer") from exc
    if minimum is not None and result < minimum:
        raise ConfigError(f"{key} must be >= {minimum}")
    return result


def _parse_csv(env: Mapping[str, str], key: str) -> list[str]:
    value = _strip(env.get(key))
    if value is None:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _load_common(env: Mapping[str, str]) -> CommonConfig:
    return CommonConfig(
        env=_strip(env.get("DOCMESH_ENV")) or "development",
        healthcheck_enabled=_parse_bool(env, "DOCMESH_HEALTHCHECK_ENABLED", default=True),
    )


def _load_keycloak(env: Mapping[str, str]) -> KeycloakConfig:
    config = KeycloakConfig(
        url=_get_required(env, "KEYCLOAK_URL"),
        realm=_get_required(env, "KEYCLOAK_REALM"),
        client_id=_get_required(env, "KEYCLOAK_CLIENT_ID"),
        client_secret=_strip(env.get("KEYCLOAK_CLIENT_SECRET")),
        verify_ssl=_parse_bool(env, "KEYCLOAK_VERIFY_SSL", default=True),
        audience=_strip(env.get("KEYCLOAK_AUDIENCE")),
        request_timeout_seconds=_parse_int(env, "KEYCLOAK_REQUEST_TIMEOUT_SECONDS", default=10, minimum=1),
        max_retries=_parse_int(env, "KEYCLOAK_MAX_RETRIES", default=3, minimum=0),
        provisioning_enabled=_parse_bool(env, "KEYCLOAK_PROVISIONING_ENABLED", default=False),
        provisioning_dry_run=_parse_bool(env, "KEYCLOAK_PROVISIONING_DRY_RUN", default=False),
        admin_realm=_strip(env.get("KEYCLOAK_ADMIN_REALM")) or "master",
        admin_client_id=_strip(env.get("KEYCLOAK_ADMIN_CLIENT_ID")) or "admin-cli",
        admin_client_secret=_strip(env.get("KEYCLOAK_ADMIN_CLIENT_SECRET")),
        admin_username=_strip(env.get("KEYCLOAK_ADMIN_USERNAME")),
        admin_password=_strip(env.get("KEYCLOAK_ADMIN_PASSWORD")),
        realm_enabled=_parse_bool(env, "KEYCLOAK_REALM_ENABLED", default=True),
        realm_display_name=_strip(env.get("KEYCLOAK_REALM_DISPLAY_NAME")),
        client_public=_parse_bool(env, "KEYCLOAK_CLIENT_PUBLIC", default=False),
        client_redirect_uris=_parse_csv(env, "KEYCLOAK_CLIENT_REDIRECT_URIS"),
        client_web_origins=_parse_csv(env, "KEYCLOAK_CLIENT_WEB_ORIGINS"),
        realm_roles=_parse_csv(env, "KEYCLOAK_REALM_ROLES"),
        client_roles=_parse_csv(env, "KEYCLOAK_CLIENT_ROLES"),
    )

    if config.provisioning_enabled:
        has_service_account = bool(config.admin_client_secret)
        has_user_credentials = bool(config.admin_username and config.admin_password)
        if has_service_account == has_user_credentials:
            raise ConfigError("KEYCLOAK provisioning requires a single admin auth mode")

    return config


def _load_postgres(env: Mapping[str, str]) -> PostgresConfig:
    dsn = _strip(env.get("POSTGRES_DSN"))
    if dsn is not None:
        return PostgresConfig(
            dsn=dsn,
            port=_parse_int(env, "POSTGRES_PORT", default=5432, minimum=1),
            sslmode=_strip(env.get("POSTGRES_SSLMODE")) or "prefer",
            connect_timeout_seconds=_parse_int(env, "POSTGRES_CONNECT_TIMEOUT_SECONDS", default=10, minimum=1),
            pool_size=_parse_int(env, "POSTGRES_POOL_SIZE", default=5, minimum=1),
            max_overflow=_parse_int(env, "POSTGRES_MAX_OVERFLOW", default=10, minimum=0),
        )

    return PostgresConfig(
        host=_get_required(env, "POSTGRES_HOST"),
        port=_parse_int(env, "POSTGRES_PORT", default=5432, minimum=1),
        db=_get_required(env, "POSTGRES_DB"),
        user=_get_required(env, "POSTGRES_USER"),
        password=_get_required(env, "POSTGRES_PASSWORD"),
        sslmode=_strip(env.get("POSTGRES_SSLMODE")) or "prefer",
        connect_timeout_seconds=_parse_int(env, "POSTGRES_CONNECT_TIMEOUT_SECONDS", default=10, minimum=1),
        pool_size=_parse_int(env, "POSTGRES_POOL_SIZE", default=5, minimum=1),
        max_overflow=_parse_int(env, "POSTGRES_MAX_OVERFLOW", default=10, minimum=0),
    )


def _load_minio(env: Mapping[str, str]) -> MinioConfig:
    return MinioConfig(
        endpoint=_get_required(env, "MINIO_ENDPOINT"),
        access_key=_get_required(env, "MINIO_ACCESS_KEY"),
        secret_key=_get_required(env, "MINIO_SECRET_KEY"),
        secure=_parse_bool(env, "MINIO_SECURE", default=True),
        region=_strip(env.get("MINIO_REGION")),
        bucket=_strip(env.get("MINIO_BUCKET")),
        request_timeout_seconds=_parse_int(env, "MINIO_REQUEST_TIMEOUT_SECONDS", default=30, minimum=1),
        max_retries=_parse_int(env, "MINIO_MAX_RETRIES", default=3, minimum=0),
    )


def _load_milvus(env: Mapping[str, str]) -> MilvusConfig:
    return MilvusConfig(
        uri=_get_required(env, "MILVUS_URI"),
        token=_strip(env.get("MILVUS_TOKEN")),
        db_name=_strip(env.get("MILVUS_DB_NAME")) or "default",
        collection=_strip(env.get("MILVUS_COLLECTION")),
        secure=_parse_bool(env, "MILVUS_SECURE", default=False),
        connect_timeout_seconds=_parse_int(env, "MILVUS_CONNECT_TIMEOUT_SECONDS", default=10, minimum=1),
        request_timeout_seconds=_parse_int(env, "MILVUS_REQUEST_TIMEOUT_SECONDS", default=30, minimum=1),
        max_retries=_parse_int(env, "MILVUS_MAX_RETRIES", default=3, minimum=0),
    )


def _load_ollama(env: Mapping[str, str]) -> OllamaConfig:
    return OllamaConfig(
        host=_get_required(env, "OLLAMA_HOST"),
        generation_model=_strip(env.get("OLLAMA_GENERATION_MODEL")),
        embedding_model=_strip(env.get("OLLAMA_EMBEDDING_MODEL")),
        request_timeout_seconds=_parse_int(env, "OLLAMA_REQUEST_TIMEOUT_SECONDS", default=120, minimum=1),
        max_retries=_parse_int(env, "OLLAMA_MAX_RETRIES", default=2, minimum=0),
    )


def _load_langfuse(env: Mapping[str, str], *, common: CommonConfig) -> LangfuseConfig:
    enabled = _parse_bool(env, "LANGFUSE_ENABLED", default=True)
    if not enabled:
        return LangfuseConfig(enabled=False, environment=common.env)

    return LangfuseConfig(
        enabled=True,
        host=_get_required(env, "LANGFUSE_HOST"),
        public_key=_get_required(env, "LANGFUSE_PUBLIC_KEY"),
        secret_key=_get_required(env, "LANGFUSE_SECRET_KEY"),
        release=_strip(env.get("LANGFUSE_RELEASE")),
        environment=_strip(env.get("LANGFUSE_ENVIRONMENT")) or common.env,
        request_timeout_seconds=_parse_int(env, "LANGFUSE_REQUEST_TIMEOUT_SECONDS", default=10, minimum=1),
        max_retries=_parse_int(env, "LANGFUSE_MAX_RETRIES", default=3, minimum=0),
    )


def _load_nats(env: Mapping[str, str]) -> NatsConfig:
    servers = _parse_csv(env, "NATS_SERVERS")
    if not servers:
        raise ConfigError("Missing required environment variable: NATS_SERVERS")

    user = _strip(env.get("NATS_USER"))
    password = _strip(env.get("NATS_PASSWORD"))
    token = _strip(env.get("NATS_TOKEN"))
    creds_file = _strip(env.get("NATS_CREDS_FILE"))

    auth_modes = [
        bool(user or password),
        bool(token),
        bool(creds_file),
    ]
    if sum(auth_modes) > 1:
        raise ConfigError("NATS requires a single authentication mode")
    if (user and not password) or (password and not user):
        raise ConfigError("NATS_USER and NATS_PASSWORD must be provided together")

    return NatsConfig(
        servers=servers,
        user=user,
        password=password,
        token=token,
        creds_file=creds_file,
        name=_strip(env.get("NATS_NAME")) or "docmesh-py-core",
        connect_timeout_seconds=_parse_int(env, "NATS_CONNECT_TIMEOUT_SECONDS", default=10, minimum=1),
        max_reconnect_attempts=_parse_int(env, "NATS_MAX_RECONNECT_ATTEMPTS", default=10, minimum=0),
    )


def _validate_security(settings: Settings) -> None:
    production_envs = {"production", "prod"}
    if settings.common.env.lower() not in production_envs:
        return

    if not settings.keycloak.verify_ssl or not settings.minio.secure or not settings.milvus.secure:
        raise ConfigError("SSL verification cannot be disabled in production")


def load_settings(env: Mapping[str, str]) -> Settings:
    common = _load_common(env)
    settings = Settings(
        common=common,
        keycloak=_load_keycloak(env),
        postgres=_load_postgres(env),
        minio=_load_minio(env),
        milvus=_load_milvus(env),
        ollama=_load_ollama(env),
        langfuse=_load_langfuse(env, common=common),
        nats=_load_nats(env),
    )
    _validate_security(settings)
    return settings
