from __future__ import annotations
from dataclasses import dataclass
import warnings
from typing import Annotated, Any, TypeVar
from pydantic import Field, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from .function_logging import log_function_boundary

class ConfigError(ValueError):
    pass
CsvList = Annotated[list[str], NoDecode]
SettingsT = TypeVar('SettingsT', bound='DocmeshBaseSettings')
SUPPORTED_SERVICES = frozenset({'keycloak', 'postgres', 'sqlite', 'minio', 'milvus', 'ollama', 'langfuse', 'nats'})

class DocmeshBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(extra='ignore', case_sensitive=False)

    @classmethod
    @log_function_boundary()
    def env_key(cls, field_name: str) -> str:
        prefix = cls.model_config.get('env_prefix', '')
        return f'{prefix}{field_name.upper()}'

    @field_validator('*', mode='before')
    @classmethod
    @log_function_boundary()
    def strip_strings(cls, value: Any) -> Any:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    @classmethod
    @log_function_boundary()
    def _parse_bool(cls, value: Any, field_name: str) -> Any:
        if value is None or isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.lower()
            if lowered == 'true':
                return True
            if lowered == 'false':
                return False
        raise ValueError(f"{cls.env_key(field_name)} must be 'true' or 'false'")

    @classmethod
    @log_function_boundary()
    def _parse_csv(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(',') if item.strip()]
        if isinstance(value, list):
            return value
        raise ValueError('must be a comma-separated string')

class CommonConfig(DocmeshBaseSettings):
    model_config = SettingsConfigDict(extra='ignore', case_sensitive=False, env_prefix='DOCMESH_')
    env: str = 'development'
    healthcheck_enabled: bool = True

    @field_validator('healthcheck_enabled', mode='before')
    @classmethod
    @log_function_boundary()
    def parse_healthcheck_enabled(cls, value: Any) -> Any:
        return cls._parse_bool(value, 'healthcheck_enabled')

class KeycloakConfig(DocmeshBaseSettings):
    model_config = SettingsConfigDict(extra='ignore', case_sensitive=False, env_prefix='KEYCLOAK_')
    url: str
    realm: str
    client_id: str
    client_secret: str | None = None
    verify_ssl: bool = True
    audience: str | None = None
    token_grant_type: str = 'client_credentials'
    token_scope: str | None = None
    token_username: str | None = None
    token_password: str | None = None
    request_timeout_seconds: int = Field(default=10, ge=1)
    max_retries: int = Field(default=3, ge=0)
    jwks_cache_ttl_seconds: int = Field(default=300, ge=0)
    provisioning_enabled: bool = False
    provisioning_dry_run: bool = False
    admin_realm: str = 'master'
    admin_client_id: str = 'admin-cli'
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

    @field_validator('verify_ssl', 'provisioning_enabled', 'provisioning_dry_run', 'realm_enabled', 'client_public', mode='before')
    @classmethod
    @log_function_boundary()
    def parse_boolean_fields(cls, value: Any, info) -> Any:
        return cls._parse_bool(value, info.field_name)

    @field_validator('client_redirect_uris', 'client_web_origins', 'realm_roles', 'client_roles', mode='before')
    @classmethod
    @log_function_boundary()
    def parse_csv_fields(cls, value: Any) -> list[str]:
        return cls._parse_csv(value)

    @field_validator('token_grant_type')
    @classmethod
    @log_function_boundary()
    def validate_token_grant_type(cls, value: str) -> str:
        allowed = {'client_credentials', 'password'}
        if value not in allowed:
            raise ValueError(f"{cls.env_key('token_grant_type')} must be one of: {', '.join(sorted(allowed))}")
        return value

    @model_validator(mode='after')
    @log_function_boundary()
    def validate_required_fields(self) -> 'KeycloakConfig':
        required_fields = {self.env_key('url'): self.url, self.env_key('realm'): self.realm, self.env_key('client_id'): self.client_id}
        missing = [name for name, value in required_fields.items() if value is None]
        if missing:
            raise ValueError(f'Missing required environment variable: {missing[0]}')
        return self

    @model_validator(mode='after')
    @log_function_boundary()
    def validate_client_secret_requirements(self) -> 'KeycloakConfig':
        if not self.client_public and self.client_secret is None:
            raise ValueError('Missing required environment variable: KEYCLOAK_CLIENT_SECRET')
        return self

    @model_validator(mode='after')
    @log_function_boundary()
    def validate_provisioning_auth_mode(self) -> 'KeycloakConfig':
        if self.provisioning_enabled:
            has_service_account = bool(self.admin_client_secret)
            has_user_credentials = bool(self.admin_username and self.admin_password)
            if has_service_account == has_user_credentials:
                raise ValueError('KEYCLOAK provisioning requires a single admin auth mode')
        return self


class PostgresConfig(DocmeshBaseSettings):
    model_config = SettingsConfigDict(extra='ignore', case_sensitive=False, env_prefix='POSTGRES_')
    dsn: str | None = None
    host: str | None = None
    port: int = Field(default=5432, ge=1)
    db: str | None = None
    user: str | None = None
    password: str | None = None
    sslmode: str = 'prefer'
    connect_timeout_seconds: int = Field(default=10, ge=1)
    pool_size: int = Field(default=5, ge=1)
    max_overflow: int = Field(default=10, ge=0)

    @model_validator(mode='after')
    @log_function_boundary()
    def validate_connection_shape(self) -> 'PostgresConfig':
        if self.dsn:
            return self
        required_fields = {self.env_key('host'): self.host, self.env_key('db'): self.db, self.env_key('user'): self.user, self.env_key('password'): self.password}
        missing = [name for name, value in required_fields.items() if value is None]
        if missing:
            raise ValueError(f'Missing required environment variable: {missing[0]}')
        return self

class SqliteConfig(DocmeshBaseSettings):
    model_config = SettingsConfigDict(extra='ignore', case_sensitive=False, env_prefix='SQLITE_')
    path: str
    readonly: bool = False
    enable_wal: bool = False
    busy_timeout_ms: int = Field(default=5000, ge=0)

    @field_validator('readonly', 'enable_wal', mode='before')
    @classmethod
    @log_function_boundary()
    def parse_boolean_fields(cls, value: Any, info) -> Any:
        return cls._parse_bool(value, info.field_name)

    @model_validator(mode='after')
    @log_function_boundary()
    def validate_required_fields(self) -> 'SqliteConfig':
        if self.path is None:
            raise ValueError(f"Missing required environment variable: {self.env_key('path')}")
        return self

class MinioConfig(DocmeshBaseSettings):
    model_config = SettingsConfigDict(extra='ignore', case_sensitive=False, env_prefix='MINIO_')
    endpoint: str
    access_key: str
    secret_key: str
    secure: bool = True
    region: str | None = None
    bucket: str | None = None
    request_timeout_seconds: int = Field(default=30, ge=1)
    max_retries: int = Field(default=3, ge=0)

    @field_validator('secure', mode='before')
    @classmethod
    @log_function_boundary()
    def parse_secure(cls, value: Any) -> Any:
        return cls._parse_bool(value, 'secure')

    @model_validator(mode='after')
    @log_function_boundary()
    def validate_required_fields(self) -> 'MinioConfig':
        required_fields = {self.env_key('endpoint'): self.endpoint, self.env_key('access_key'): self.access_key, self.env_key('secret_key'): self.secret_key}
        missing = [name for name, value in required_fields.items() if value is None]
        if missing:
            raise ValueError(f'Missing required environment variable: {missing[0]}')
        return self

class MilvusConfig(DocmeshBaseSettings):
    model_config = SettingsConfigDict(extra='ignore', case_sensitive=False, env_prefix='MILVUS_')
    uri: str
    token: str | None = None
    db_name: str = 'default'
    collection: str | None = None
    secure: bool = False
    connect_timeout_seconds: int = Field(default=10, ge=1)
    request_timeout_seconds: int = Field(default=30, ge=1)
    max_retries: int = Field(default=3, ge=0)

    @field_validator('secure', mode='before')
    @classmethod
    @log_function_boundary()
    def parse_secure(cls, value: Any) -> Any:
        return cls._parse_bool(value, 'secure')

    @model_validator(mode='after')
    @log_function_boundary()
    def validate_required_fields(self) -> 'MilvusConfig':
        if self.uri is None:
            raise ValueError(f"Missing required environment variable: {self.env_key('uri')}")
        return self

class OllamaConfig(DocmeshBaseSettings):
    model_config = SettingsConfigDict(extra='ignore', case_sensitive=False, env_prefix='OLLAMA_')
    host: str
    generation_model: str | None = None
    embedding_model: str | None = None
    request_timeout_seconds: int = Field(default=120, ge=1)
    max_retries: int = Field(default=2, ge=0)

    @model_validator(mode='after')
    @log_function_boundary()
    def validate_required_fields(self) -> 'OllamaConfig':
        if self.host is None:
            raise ValueError(f"Missing required environment variable: {self.env_key('host')}")
        return self

class LangfuseConfig(DocmeshBaseSettings):
    model_config = SettingsConfigDict(extra='ignore', case_sensitive=False, env_prefix='LANGFUSE_')
    enabled: bool = True
    host: str | None = None
    public_key: str | None = None
    secret_key: str | None = None
    release: str | None = None
    environment: str | None = None
    request_timeout_seconds: int = Field(default=10, ge=1)
    max_retries: int = Field(default=3, ge=0)

    @field_validator('enabled', mode='before')
    @classmethod
    @log_function_boundary()
    def parse_enabled(cls, value: Any) -> Any:
        return cls._parse_bool(value, 'enabled')

    @model_validator(mode='after')
    @log_function_boundary()
    def validate_required_when_enabled(self) -> 'LangfuseConfig':
        if not self.enabled:
            return self
        required_fields = {self.env_key('host'): self.host, self.env_key('public_key'): self.public_key, self.env_key('secret_key'): self.secret_key}
        missing = [name for name, value in required_fields.items() if value is None]
        if missing:
            raise ValueError(f'Missing required environment variable: {missing[0]}')
        return self

class NatsConfig(DocmeshBaseSettings):
    model_config = SettingsConfigDict(extra='ignore', case_sensitive=False, env_prefix='NATS_')
    servers: CsvList = Field(default_factory=list)
    user: str | None = None
    password: str | None = None
    token: str | None = None
    creds_file: str | None = None
    name: str = 'docmesh-py-core'
    connect_timeout_seconds: int = Field(default=10, ge=1)
    max_reconnect_attempts: int = Field(default=10, ge=0)

    @field_validator('servers', mode='before')
    @classmethod
    @log_function_boundary()
    def parse_servers(cls, value: Any) -> list[str]:
        return cls._parse_csv(value)

    @model_validator(mode='after')
    @log_function_boundary()
    def validate_auth_modes(self) -> 'NatsConfig':
        if not self.servers:
            raise ValueError('Missing required environment variable: NATS_SERVERS')
        auth_modes = [bool(self.user or self.password), bool(self.token), bool(self.creds_file)]
        if sum(auth_modes) > 1:
            raise ValueError('NATS requires a single authentication mode')
        if self.user and (not self.password) or (self.password and (not self.user)):
            raise ValueError('NATS_USER and NATS_PASSWORD must be provided together')
        return self

@dataclass
class ServiceConfigs:
    common: CommonConfig
    keycloak: KeycloakConfig | None = None
    postgres: PostgresConfig | None = None
    sqlite: SqliteConfig | None = None
    minio: MinioConfig | None = None
    milvus: MilvusConfig | None = None
    ollama: OllamaConfig | None = None
    langfuse: LangfuseConfig | None = None
    nats: NatsConfig | None = None

    @property
    @log_function_boundary()
    def docmesh_env(self) -> str:
        return self.common.env

@log_function_boundary()
def _normalize_requested_services(services: set[str] | None) -> set[str]:
    if services is None:
        return set(SUPPORTED_SERVICES)
    normalized = {service.lower() for service in services}
    unknown = sorted(normalized.difference(SUPPORTED_SERVICES))
    if unknown:
        raise ConfigError(f'Unsupported services requested: {", ".join(unknown)}')
    return normalized

@log_function_boundary()
def _rewrite_validation_message(settings_cls: type[SettingsT], exc: ValidationError) -> str:
    rewritten_lines: list[str] = []
    for error in exc.errors():
        loc = error.get('loc', ())
        field_name = loc[0] if loc else None
        field_label = settings_cls.env_key(field_name) if isinstance(field_name, str) else str(field_name)
        message = error.get('msg', 'Invalid configuration')
        if error.get('type') == 'missing':
            rewritten = f'Missing required environment variable: {field_label}'
        elif field_name:
            rewritten = f'{field_label}: {message}'
        else:
            rewritten = message
        rewritten_lines.append(rewritten)
    return '\n'.join(dict.fromkeys(rewritten_lines))

@log_function_boundary()
def _load_runtime_settings(settings_cls: type[SettingsT]) -> SettingsT:
    try:
        return settings_cls()
    except ValidationError as exc:
        raise ConfigError(_rewrite_validation_message(settings_cls, exc)) from exc

@log_function_boundary()
def load_common_config() -> CommonConfig:
    return _load_runtime_settings(CommonConfig)

@log_function_boundary()
def require_keycloak_config() -> KeycloakConfig:
    return _load_runtime_settings(KeycloakConfig)

@log_function_boundary()
def require_minio_config() -> MinioConfig:
    return _load_runtime_settings(MinioConfig)

@log_function_boundary()
def require_milvus_config() -> MilvusConfig:
    return _load_runtime_settings(MilvusConfig)

@log_function_boundary()
def require_ollama_config() -> OllamaConfig:
    return _load_runtime_settings(OllamaConfig)

@log_function_boundary()
def require_langfuse_config(*, common: CommonConfig | None=None) -> LangfuseConfig:
    langfuse = _load_runtime_settings(LangfuseConfig)
    return apply_langfuse_defaults(common or load_common_config(), langfuse)

@log_function_boundary()
def require_nats_config() -> NatsConfig:
    return _load_runtime_settings(NatsConfig)

@log_function_boundary()
def apply_langfuse_defaults(common: CommonConfig, langfuse: LangfuseConfig | None) -> LangfuseConfig | None:
    if langfuse is not None and langfuse.environment is None:
        langfuse.environment = common.env
    return langfuse

@log_function_boundary()
def validate_runtime_security(common: CommonConfig, *, keycloak: KeycloakConfig | None=None, minio: MinioConfig | None=None, milvus: MilvusConfig | None=None) -> None:
    if common.env.lower() not in {'production', 'prod'}:
        return
    if ((keycloak is not None and (not keycloak.verify_ssl)) or (minio is not None and (not minio.secure)) or (milvus is not None and (not milvus.secure))):
        raise ConfigError('SSL verification cannot be disabled in production')

@log_function_boundary()
def load_service_configs(*, services: set[str] | None=None) -> ServiceConfigs:
    common = load_common_config()
    selected_services = _normalize_requested_services(services)
    service_configs = ServiceConfigs(common=common, keycloak=(require_keycloak_config() if 'keycloak' in selected_services else None), postgres=(_load_runtime_settings(PostgresConfig) if 'postgres' in selected_services else None), sqlite=(_load_runtime_settings(SqliteConfig) if 'sqlite' in selected_services else None), minio=(require_minio_config() if 'minio' in selected_services else None), milvus=(require_milvus_config() if 'milvus' in selected_services else None), ollama=(require_ollama_config() if 'ollama' in selected_services else None), langfuse=(require_langfuse_config(common=common) if 'langfuse' in selected_services else None), nats=(require_nats_config() if 'nats' in selected_services else None))
    validate_runtime_security(common, keycloak=service_configs.keycloak, minio=service_configs.minio, milvus=service_configs.milvus)
    return service_configs

@log_function_boundary()
def load_settings(*, services: set[str] | None=None) -> ServiceConfigs:
    warnings.warn(
        'load_settings() is deprecated; use load_service_configs() instead.',
        DeprecationWarning,
        stacklevel=2,
    )
    return load_service_configs(services=services)
