from __future__ import annotations

from typing import Annotated, Any, Mapping, TypeVar

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class ConfigError(ValueError):
    pass


CsvList = Annotated[list[str], NoDecode]
SettingsT = TypeVar("SettingsT", bound="DocmeshBaseSettings")


class DocmeshBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=True)

    @field_validator("*", mode="before")
    @classmethod
    def strip_strings(cls, value: Any) -> Any:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    @classmethod
    def _parse_bool(cls, value: Any, field_name: str) -> Any:
        if value is None or isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.lower()
            if lowered == "true":
                return True
            if lowered == "false":
                return False
        raise ValueError(f"{field_name} must be 'true' or 'false'")

    @classmethod
    def _parse_csv(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, list):
            return value
        raise ValueError("must be a comma-separated string")


class CommonConfig(DocmeshBaseSettings):
    env: str = Field(default="development", validation_alias="DOCMESH_ENV")
    healthcheck_enabled: bool = Field(default=True, validation_alias="DOCMESH_HEALTHCHECK_ENABLED")

    @field_validator("healthcheck_enabled", mode="before")
    @classmethod
    def parse_healthcheck_enabled(cls, value: Any) -> Any:
        return cls._parse_bool(value, "DOCMESH_HEALTHCHECK_ENABLED")


class KeycloakConfig(DocmeshBaseSettings):
    url: str = Field(validation_alias="KEYCLOAK_URL")
    realm: str = Field(validation_alias="KEYCLOAK_REALM")
    client_id: str = Field(validation_alias="KEYCLOAK_CLIENT_ID")
    client_secret: str | None = Field(default=None, validation_alias="KEYCLOAK_CLIENT_SECRET")
    verify_ssl: bool = Field(default=True, validation_alias="KEYCLOAK_VERIFY_SSL")
    audience: str | None = Field(default=None, validation_alias="KEYCLOAK_AUDIENCE")
    request_timeout_seconds: int = Field(default=10, ge=1, validation_alias="KEYCLOAK_REQUEST_TIMEOUT_SECONDS")
    max_retries: int = Field(default=3, ge=0, validation_alias="KEYCLOAK_MAX_RETRIES")
    provisioning_enabled: bool = Field(default=False, validation_alias="KEYCLOAK_PROVISIONING_ENABLED")
    provisioning_dry_run: bool = Field(default=False, validation_alias="KEYCLOAK_PROVISIONING_DRY_RUN")
    admin_realm: str = Field(default="master", validation_alias="KEYCLOAK_ADMIN_REALM")
    admin_client_id: str = Field(default="admin-cli", validation_alias="KEYCLOAK_ADMIN_CLIENT_ID")
    admin_client_secret: str | None = Field(default=None, validation_alias="KEYCLOAK_ADMIN_CLIENT_SECRET")
    admin_username: str | None = Field(default=None, validation_alias="KEYCLOAK_ADMIN_USERNAME")
    admin_password: str | None = Field(default=None, validation_alias="KEYCLOAK_ADMIN_PASSWORD")
    realm_enabled: bool = Field(default=True, validation_alias="KEYCLOAK_REALM_ENABLED")
    realm_display_name: str | None = Field(default=None, validation_alias="KEYCLOAK_REALM_DISPLAY_NAME")
    client_public: bool = Field(default=False, validation_alias="KEYCLOAK_CLIENT_PUBLIC")
    client_redirect_uris: CsvList = Field(default_factory=list, validation_alias="KEYCLOAK_CLIENT_REDIRECT_URIS")
    client_web_origins: CsvList = Field(default_factory=list, validation_alias="KEYCLOAK_CLIENT_WEB_ORIGINS")
    realm_roles: CsvList = Field(default_factory=list, validation_alias="KEYCLOAK_REALM_ROLES")
    client_roles: CsvList = Field(default_factory=list, validation_alias="KEYCLOAK_CLIENT_ROLES")

    @field_validator(
        "verify_ssl",
        "provisioning_enabled",
        "provisioning_dry_run",
        "realm_enabled",
        "client_public",
        mode="before",
    )
    @classmethod
    def parse_boolean_fields(cls, value: Any, info) -> Any:
        return cls._parse_bool(value, info.field_name.upper())

    @field_validator(
        "client_redirect_uris",
        "client_web_origins",
        "realm_roles",
        "client_roles",
        mode="before",
    )
    @classmethod
    def parse_csv_fields(cls, value: Any) -> list[str]:
        return cls._parse_csv(value)

    @model_validator(mode="after")
    def validate_provisioning_auth_mode(self) -> "KeycloakConfig":
        if self.provisioning_enabled:
            has_service_account = bool(self.admin_client_secret)
            has_user_credentials = bool(self.admin_username and self.admin_password)
            if has_service_account == has_user_credentials:
                raise ValueError("KEYCLOAK provisioning requires a single admin auth mode")
        return self


class PostgresConfig(DocmeshBaseSettings):
    dsn: str | None = Field(default=None, validation_alias="POSTGRES_DSN")
    host: str | None = Field(default=None, validation_alias="POSTGRES_HOST")
    port: int = Field(default=5432, ge=1, validation_alias="POSTGRES_PORT")
    db: str | None = Field(default=None, validation_alias="POSTGRES_DB")
    user: str | None = Field(default=None, validation_alias="POSTGRES_USER")
    password: str | None = Field(default=None, validation_alias="POSTGRES_PASSWORD")
    sslmode: str = Field(default="prefer", validation_alias="POSTGRES_SSLMODE")
    connect_timeout_seconds: int = Field(default=10, ge=1, validation_alias="POSTGRES_CONNECT_TIMEOUT_SECONDS")
    pool_size: int = Field(default=5, ge=1, validation_alias="POSTGRES_POOL_SIZE")
    max_overflow: int = Field(default=10, ge=0, validation_alias="POSTGRES_MAX_OVERFLOW")

    @model_validator(mode="after")
    def validate_connection_shape(self) -> "PostgresConfig":
        if self.dsn:
            return self
        required_fields = {
            "POSTGRES_HOST": self.host,
            "POSTGRES_DB": self.db,
            "POSTGRES_USER": self.user,
            "POSTGRES_PASSWORD": self.password,
        }
        missing = [name for name, value in required_fields.items() if value is None]
        if missing:
            raise ValueError(f"Missing required environment variable: {missing[0]}")
        return self


class MinioConfig(DocmeshBaseSettings):
    endpoint: str = Field(validation_alias="MINIO_ENDPOINT")
    access_key: str = Field(validation_alias="MINIO_ACCESS_KEY")
    secret_key: str = Field(validation_alias="MINIO_SECRET_KEY")
    secure: bool = Field(default=True, validation_alias="MINIO_SECURE")
    region: str | None = Field(default=None, validation_alias="MINIO_REGION")
    bucket: str | None = Field(default=None, validation_alias="MINIO_BUCKET")
    request_timeout_seconds: int = Field(default=30, ge=1, validation_alias="MINIO_REQUEST_TIMEOUT_SECONDS")
    max_retries: int = Field(default=3, ge=0, validation_alias="MINIO_MAX_RETRIES")

    @field_validator("secure", mode="before")
    @classmethod
    def parse_secure(cls, value: Any) -> Any:
        return cls._parse_bool(value, "MINIO_SECURE")


class MilvusConfig(DocmeshBaseSettings):
    uri: str = Field(validation_alias="MILVUS_URI")
    token: str | None = Field(default=None, validation_alias="MILVUS_TOKEN")
    db_name: str = Field(default="default", validation_alias="MILVUS_DB_NAME")
    collection: str | None = Field(default=None, validation_alias="MILVUS_COLLECTION")
    secure: bool = Field(default=False, validation_alias="MILVUS_SECURE")
    connect_timeout_seconds: int = Field(default=10, ge=1, validation_alias="MILVUS_CONNECT_TIMEOUT_SECONDS")
    request_timeout_seconds: int = Field(default=30, ge=1, validation_alias="MILVUS_REQUEST_TIMEOUT_SECONDS")
    max_retries: int = Field(default=3, ge=0, validation_alias="MILVUS_MAX_RETRIES")

    @field_validator("secure", mode="before")
    @classmethod
    def parse_secure(cls, value: Any) -> Any:
        return cls._parse_bool(value, "MILVUS_SECURE")


class OllamaConfig(DocmeshBaseSettings):
    host: str = Field(validation_alias="OLLAMA_HOST")
    generation_model: str | None = Field(default=None, validation_alias="OLLAMA_GENERATION_MODEL")
    embedding_model: str | None = Field(default=None, validation_alias="OLLAMA_EMBEDDING_MODEL")
    request_timeout_seconds: int = Field(default=120, ge=1, validation_alias="OLLAMA_REQUEST_TIMEOUT_SECONDS")
    max_retries: int = Field(default=2, ge=0, validation_alias="OLLAMA_MAX_RETRIES")


class LangfuseConfig(DocmeshBaseSettings):
    enabled: bool = Field(default=True, validation_alias="LANGFUSE_ENABLED")
    host: str | None = Field(default=None, validation_alias="LANGFUSE_HOST")
    public_key: str | None = Field(default=None, validation_alias="LANGFUSE_PUBLIC_KEY")
    secret_key: str | None = Field(default=None, validation_alias="LANGFUSE_SECRET_KEY")
    release: str | None = Field(default=None, validation_alias="LANGFUSE_RELEASE")
    environment: str | None = Field(default=None, validation_alias="LANGFUSE_ENVIRONMENT")
    request_timeout_seconds: int = Field(default=10, ge=1, validation_alias="LANGFUSE_REQUEST_TIMEOUT_SECONDS")
    max_retries: int = Field(default=3, ge=0, validation_alias="LANGFUSE_MAX_RETRIES")

    @field_validator("enabled", mode="before")
    @classmethod
    def parse_enabled(cls, value: Any) -> Any:
        return cls._parse_bool(value, "LANGFUSE_ENABLED")

    @model_validator(mode="after")
    def validate_required_when_enabled(self) -> "LangfuseConfig":
        if not self.enabled:
            return self
        required_fields = {
            "LANGFUSE_HOST": self.host,
            "LANGFUSE_PUBLIC_KEY": self.public_key,
            "LANGFUSE_SECRET_KEY": self.secret_key,
        }
        missing = [name for name, value in required_fields.items() if value is None]
        if missing:
            raise ValueError(f"Missing required environment variable: {missing[0]}")
        return self


class NatsConfig(DocmeshBaseSettings):
    servers: CsvList = Field(validation_alias="NATS_SERVERS")
    user: str | None = Field(default=None, validation_alias="NATS_USER")
    password: str | None = Field(default=None, validation_alias="NATS_PASSWORD")
    token: str | None = Field(default=None, validation_alias="NATS_TOKEN")
    creds_file: str | None = Field(default=None, validation_alias="NATS_CREDS_FILE")
    name: str = Field(default="docmesh-py-core", validation_alias="NATS_NAME")
    connect_timeout_seconds: int = Field(default=10, ge=1, validation_alias="NATS_CONNECT_TIMEOUT_SECONDS")
    max_reconnect_attempts: int = Field(default=10, ge=0, validation_alias="NATS_MAX_RECONNECT_ATTEMPTS")

    @field_validator("servers", mode="before")
    @classmethod
    def parse_servers(cls, value: Any) -> list[str]:
        return cls._parse_csv(value)

    @model_validator(mode="after")
    def validate_auth_modes(self) -> "NatsConfig":
        if not self.servers:
            raise ValueError("Missing required environment variable: NATS_SERVERS")

        auth_modes = [
            bool(self.user or self.password),
            bool(self.token),
            bool(self.creds_file),
        ]
        if sum(auth_modes) > 1:
            raise ValueError("NATS requires a single authentication mode")
        if (self.user and not self.password) or (self.password and not self.user):
            raise ValueError("NATS_USER and NATS_PASSWORD must be provided together")
        return self


class Settings(BaseModel):
    common: CommonConfig
    keycloak: KeycloakConfig
    postgres: PostgresConfig
    minio: MinioConfig
    milvus: MilvusConfig
    ollama: OllamaConfig
    langfuse: LangfuseConfig
    nats: NatsConfig


def _build_settings(settings_cls: type[SettingsT], env: Mapping[str, str]) -> SettingsT:
    try:
        return settings_cls.model_validate(dict(env))
    except ValidationError as exc:
        raise ConfigError(str(exc)) from exc


def _validate_security(settings: Settings) -> None:
    if settings.common.env.lower() not in {"production", "prod"}:
        return
    if not settings.keycloak.verify_ssl or not settings.minio.secure or not settings.milvus.secure:
        raise ConfigError("SSL verification cannot be disabled in production")


def load_settings(env: Mapping[str, str]) -> Settings:
    common = _build_settings(CommonConfig, env)
    settings = Settings(
        common=common,
        keycloak=_build_settings(KeycloakConfig, env),
        postgres=_build_settings(PostgresConfig, env),
        minio=_build_settings(MinioConfig, env),
        milvus=_build_settings(MilvusConfig, env),
        ollama=_build_settings(OllamaConfig, env),
        langfuse=_build_settings(LangfuseConfig, {**dict(env), "LANGFUSE_ENVIRONMENT": env.get("LANGFUSE_ENVIRONMENT", common.env)}),
        nats=_build_settings(NatsConfig, env),
    )
    _validate_security(settings)
    return settings
