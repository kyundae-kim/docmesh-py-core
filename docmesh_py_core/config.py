from __future__ import annotations

from typing import Annotated, Any, Mapping, TypeVar

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class ConfigError(ValueError):
    pass


CsvList = Annotated[list[str], NoDecode]
SettingsT = TypeVar("SettingsT", bound="DocmeshBaseSettings")


class DocmeshBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)

    @classmethod
    def env_key(cls, field_name: str) -> str:
        prefix = cls.model_config.get("env_prefix", "")
        return f"{prefix}{field_name.upper()}"

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
        raise ValueError(f"{cls.env_key(field_name)} must be 'true' or 'false'")

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
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False, env_prefix="DOCMESH_")

    env: str = "development"
    healthcheck_enabled: bool = True

    @field_validator("healthcheck_enabled", mode="before")
    @classmethod
    def parse_healthcheck_enabled(cls, value: Any) -> Any:
        return cls._parse_bool(value, "healthcheck_enabled")


class KeycloakConfig(DocmeshBaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False, env_prefix="KEYCLOAK_")

    url: str
    realm: str
    client_id: str
    client_secret: str | None = None
    verify_ssl: bool = True
    audience: str | None = None
    token_grant_type: str = "client_credentials"
    token_scope: str | None = None
    token_username: str | None = None
    token_password: str | None = None
    request_timeout_seconds: int = Field(default=10, ge=1)
    max_retries: int = Field(default=3, ge=0)
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
    client_redirect_uris: CsvList = Field(default_factory=list)
    client_web_origins: CsvList = Field(default_factory=list)
    realm_roles: CsvList = Field(default_factory=list)
    client_roles: CsvList = Field(default_factory=list)

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
        return cls._parse_bool(value, info.field_name)

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

    @field_validator("token_grant_type")
    @classmethod
    def validate_token_grant_type(cls, value: str) -> str:
        allowed = {"client_credentials", "password"}
        if value not in allowed:
            raise ValueError(
                f"{cls.env_key('token_grant_type')} must be one of: {', '.join(sorted(allowed))}"
            )
        return value

    @model_validator(mode="after")
    def validate_required_fields(self) -> "KeycloakConfig":
        required_fields = {
            self.env_key("url"): self.url,
            self.env_key("realm"): self.realm,
            self.env_key("client_id"): self.client_id,
        }
        missing = [name for name, value in required_fields.items() if value is None]
        if missing:
            raise ValueError(f"Missing required environment variable: {missing[0]}")
        return self

    @model_validator(mode="after")
    def validate_client_secret_requirements(self) -> "KeycloakConfig":
        if not self.client_public and self.client_secret is None:
            raise ValueError("Missing required environment variable: KEYCLOAK_CLIENT_SECRET")
        return self

    @model_validator(mode="after")
    def validate_provisioning_auth_mode(self) -> "KeycloakConfig":
        if self.provisioning_enabled:
            has_service_account = bool(self.admin_client_secret)
            has_user_credentials = bool(self.admin_username and self.admin_password)
            if has_service_account == has_user_credentials:
                raise ValueError("KEYCLOAK provisioning requires a single admin auth mode")
        return self

    @model_validator(mode="after")
    def validate_token_grant_requirements(self) -> "KeycloakConfig":
        if self.token_grant_type == "password" and not (self.token_username and self.token_password):
            missing = "KEYCLOAK_TOKEN_USERNAME" if not self.token_username else "KEYCLOAK_TOKEN_PASSWORD"
            raise ValueError(f"Missing required environment variable: {missing}")
        return self


class PostgresConfig(DocmeshBaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False, env_prefix="POSTGRES_")

    dsn: str | None = None
    host: str | None = None
    port: int = Field(default=5432, ge=1)
    db: str | None = None
    user: str | None = None
    password: str | None = None
    sslmode: str = "prefer"
    connect_timeout_seconds: int = Field(default=10, ge=1)
    pool_size: int = Field(default=5, ge=1)
    max_overflow: int = Field(default=10, ge=0)

    @model_validator(mode="after")
    def validate_connection_shape(self) -> "PostgresConfig":
        if self.dsn:
            return self
        required_fields = {
            self.env_key("host"): self.host,
            self.env_key("db"): self.db,
            self.env_key("user"): self.user,
            self.env_key("password"): self.password,
        }
        missing = [name for name, value in required_fields.items() if value is None]
        if missing:
            raise ValueError(f"Missing required environment variable: {missing[0]}")
        return self


class MinioConfig(DocmeshBaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False, env_prefix="MINIO_")

    endpoint: str
    access_key: str
    secret_key: str
    secure: bool = True
    region: str | None = None
    bucket: str | None = None
    request_timeout_seconds: int = Field(default=30, ge=1)
    max_retries: int = Field(default=3, ge=0)

    @field_validator("secure", mode="before")
    @classmethod
    def parse_secure(cls, value: Any) -> Any:
        return cls._parse_bool(value, "secure")

    @model_validator(mode="after")
    def validate_required_fields(self) -> "MinioConfig":
        required_fields = {
            self.env_key("endpoint"): self.endpoint,
            self.env_key("access_key"): self.access_key,
            self.env_key("secret_key"): self.secret_key,
        }
        missing = [name for name, value in required_fields.items() if value is None]
        if missing:
            raise ValueError(f"Missing required environment variable: {missing[0]}")
        return self


class MilvusConfig(DocmeshBaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False, env_prefix="MILVUS_")

    uri: str
    token: str | None = None
    db_name: str = "default"
    collection: str | None = None
    secure: bool = False
    connect_timeout_seconds: int = Field(default=10, ge=1)
    request_timeout_seconds: int = Field(default=30, ge=1)
    max_retries: int = Field(default=3, ge=0)

    @field_validator("secure", mode="before")
    @classmethod
    def parse_secure(cls, value: Any) -> Any:
        return cls._parse_bool(value, "secure")

    @model_validator(mode="after")
    def validate_required_fields(self) -> "MilvusConfig":
        if self.uri is None:
            raise ValueError(f"Missing required environment variable: {self.env_key('uri')}")
        return self


class OllamaConfig(DocmeshBaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False, env_prefix="OLLAMA_")

    host: str
    generation_model: str | None = None
    embedding_model: str | None = None
    request_timeout_seconds: int = Field(default=120, ge=1)
    max_retries: int = Field(default=2, ge=0)

    @model_validator(mode="after")
    def validate_required_fields(self) -> "OllamaConfig":
        if self.host is None:
            raise ValueError(f"Missing required environment variable: {self.env_key('host')}")
        return self


class LangfuseConfig(DocmeshBaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False, env_prefix="LANGFUSE_")

    enabled: bool = True
    host: str | None = None
    public_key: str | None = None
    secret_key: str | None = None
    release: str | None = None
    environment: str | None = None
    request_timeout_seconds: int = Field(default=10, ge=1)
    max_retries: int = Field(default=3, ge=0)

    @field_validator("enabled", mode="before")
    @classmethod
    def parse_enabled(cls, value: Any) -> Any:
        return cls._parse_bool(value, "enabled")

    @model_validator(mode="after")
    def validate_required_when_enabled(self) -> "LangfuseConfig":
        if not self.enabled:
            return self
        required_fields = {
            self.env_key("host"): self.host,
            self.env_key("public_key"): self.public_key,
            self.env_key("secret_key"): self.secret_key,
        }
        missing = [name for name, value in required_fields.items() if value is None]
        if missing:
            raise ValueError(f"Missing required environment variable: {missing[0]}")
        return self


class NatsConfig(DocmeshBaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False, env_prefix="NATS_")

    servers: CsvList = Field(default_factory=list)
    user: str | None = None
    password: str | None = None
    token: str | None = None
    creds_file: str | None = None
    name: str = "docmesh-py-core"
    connect_timeout_seconds: int = Field(default=10, ge=1)
    max_reconnect_attempts: int = Field(default=10, ge=0)

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


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)

    common: CommonConfig = Field(default_factory=lambda: CommonConfig())
    keycloak: KeycloakConfig = Field(default_factory=lambda: KeycloakConfig())
    postgres: PostgresConfig = Field(default_factory=lambda: PostgresConfig())
    minio: MinioConfig = Field(default_factory=lambda: MinioConfig())
    milvus: MilvusConfig = Field(default_factory=lambda: MilvusConfig())
    ollama: OllamaConfig = Field(default_factory=lambda: OllamaConfig())
    langfuse: LangfuseConfig = Field(default_factory=lambda: LangfuseConfig())
    nats: NatsConfig = Field(default_factory=lambda: NatsConfig())

    @model_validator(mode="after")
    def apply_cross_service_defaults(self) -> "Settings":
        if self.langfuse.environment is None:
            self.langfuse.environment = self.common.env
        _validate_security(self)
        return self


def _settings_kwargs_from_env(settings_cls: type[SettingsT], env: Mapping[str, str]) -> dict[str, Any]:
    prefix = settings_cls.model_config.get("env_prefix", "")
    kwargs: dict[str, Any] = {}
    for field_name in settings_cls.model_fields:
        env_key = f"{prefix}{field_name.upper()}"
        if env_key in env:
            kwargs[field_name] = env[env_key]
    return kwargs


def _rewrite_validation_message(settings_cls: type[SettingsT], exc: ValidationError) -> str:
    rewritten_lines: list[str] = []
    for error in exc.errors():
        loc = error.get("loc", ())
        field_name = loc[0] if loc else None
        field_label = settings_cls.env_key(field_name) if isinstance(field_name, str) else str(field_name)
        message = error.get("msg", "Invalid configuration")
        if error.get("type") == "missing":
            rewritten = f"Missing required environment variable: {field_label}"
        elif field_name:
            rewritten = f"{field_label}: {message}"
        else:
            rewritten = message
        rewritten_lines.append(rewritten)
    return "\n".join(dict.fromkeys(rewritten_lines))


def _build_settings(settings_cls: type[SettingsT], env: Mapping[str, str]) -> SettingsT:
    try:
        return settings_cls(**_settings_kwargs_from_env(settings_cls, env))
    except ValidationError as exc:
        raise ConfigError(_rewrite_validation_message(settings_cls, exc)) from exc


def _validate_security(settings: Settings) -> None:
    if settings.common.env.lower() not in {"production", "prod"}:
        return
    if not settings.keycloak.verify_ssl or not settings.minio.secure or not settings.milvus.secure:
        raise ConfigError("SSL verification cannot be disabled in production")


def load_settings(env: Mapping[str, str]) -> Settings:
    common = _build_settings(CommonConfig, env)
    langfuse_env = dict(env)
    langfuse_env.setdefault("LANGFUSE_ENVIRONMENT", common.env)
    try:
        return Settings(
            common=common,
            keycloak=_build_settings(KeycloakConfig, env),
            postgres=_build_settings(PostgresConfig, env),
            minio=_build_settings(MinioConfig, env),
            milvus=_build_settings(MilvusConfig, env),
            ollama=_build_settings(OllamaConfig, env),
            langfuse=_build_settings(LangfuseConfig, langfuse_env),
            nats=_build_settings(NatsConfig, env),
        )
    except ValidationError as exc:
        raise ConfigError(str(exc)) from exc
