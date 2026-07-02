from __future__ import annotations
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field
import inspect
from pathlib import Path
from typing import Any

from langfuse import Langfuse
from minio import Minio
from nats import connect as nats_connect
from ollama import Client as OllamaClient
from pymilvus import MilvusClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL, make_url

from .config import KeycloakConfig, LangfuseConfig, MilvusConfig, MinioConfig, NatsConfig, OllamaConfig, PostgresConfig, SqliteConfig
from .function_logging import log_function_boundary
from .keycloak import KeycloakAuthService
from .security import mask_sensitive_value

HealthCheck = Callable[[], Any]


class ServiceClientError(RuntimeError):

    @log_function_boundary()
    def __init__(self, *, service: str, operation: str, error_type: str, error: str):
        super().__init__(f'{service} {operation} failed ({error_type}): {error}')
        self.service = service
        self.operation = operation
        self.error_type = error_type
        self.error = error


class ServiceClientWrapperError(ServiceClientError):
    pass


@dataclass
class ServiceClientWrapper:
    client: Any
    healthcheck: HealthCheck
    service_name: str = 'unknown'
    close_fn: Callable[[], Any] | None = None

    @log_function_boundary()
    def ping(self) -> Any:
        try:
            return self.healthcheck()
        except Exception as exc:
            raise ServiceClientWrapperError(
                service=self.service_name,
                operation='healthcheck',
                error_type=_error_type(exc),
                error=mask_sensitive_value(str(exc)) or 'unknown error',
            ) from exc

    @log_function_boundary()
    def check(self) -> Any:
        return self.ping()

    @log_function_boundary()
    def close(self) -> Any:
        if self.close_fn is not None:
            return self.close_fn()
        close_method = getattr(self.client, 'close', None)
        if callable(close_method):
            return close_method()
        return None

    @log_function_boundary()
    def __getattr__(self, name: str) -> Any:
        return getattr(self.client, name)


@dataclass(frozen=True)
class NatsConnectionBuilder:
    servers: list[str]
    name: str
    connect_timeout_seconds: int
    max_reconnect_attempts: int
    user: str | None = None
    password: str | None = None
    token: str | None = None
    creds_file: str | None = None
    _connect_fn: Callable[..., Awaitable[Any]] = field(default=nats_connect, repr=False, compare=False)

    @property
    @log_function_boundary()
    def connect_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            'servers': self.servers,
            'name': self.name,
            'connect_timeout': self.connect_timeout_seconds,
            'max_reconnect_attempts': self.max_reconnect_attempts,
        }
        if self.user is not None:
            kwargs['user'] = self.user
        if self.password is not None:
            kwargs['password'] = self.password
        if self.token is not None:
            kwargs['token'] = self.token
        if self.creds_file is not None:
            kwargs['user_credentials'] = self.creds_file
        return kwargs

    @log_function_boundary()
    async def connect(self) -> Any:
        result = self._connect_fn(**self.connect_kwargs)
        if inspect.isawaitable(result):
            return await result
        return result

    @log_function_boundary()
    async def ping(self) -> Any:
        client = await self.connect()
        try:
            flush_method = getattr(client, 'flush', None)
            if callable(flush_method):
                await flush_method()
            return client
        finally:
            await _close_async_client(client)

    @log_function_boundary()
    async def check(self) -> Any:
        return await self.ping()


@log_function_boundary()
def create_keycloak_client(config: KeycloakConfig) -> ServiceClientWrapper:
    client = KeycloakAuthService(config)
    return ServiceClientWrapper(client=client, service_name='keycloak', healthcheck=client.fetch_access_token)


@log_function_boundary()
def create_postgres_client(config: PostgresConfig) -> ServiceClientWrapper:
    client = create_engine(
        _postgres_url(config),
        pool_size=config.pool_size,
        max_overflow=config.max_overflow,
        connect_args={'connect_timeout': config.connect_timeout_seconds, 'sslmode': config.sslmode},
    )
    return ServiceClientWrapper(client=client, service_name='postgres', healthcheck=lambda: _check_postgres(client), close_fn=client.dispose)


@log_function_boundary()
def create_sqlite_client(config: SqliteConfig) -> ServiceClientWrapper:
    client = create_engine(
        _sqlite_url(config),
        connect_args={'timeout': config.busy_timeout_ms / 1000, 'check_same_thread': False},
    )
    _configure_sqlite_engine(client, config)
    return ServiceClientWrapper(client=client, service_name='sqlite', healthcheck=lambda: _check_postgres(client), close_fn=client.dispose)


@log_function_boundary()
def create_minio_client(config: MinioConfig) -> ServiceClientWrapper:
    client = Minio(
        config.endpoint,
        access_key=config.access_key,
        secret_key=config.secret_key,
        secure=config.secure,
        region=config.region,
        cert_check=config.secure,
    )
    return ServiceClientWrapper(client=client, service_name='minio', healthcheck=client.list_buckets)


@log_function_boundary()
def create_milvus_client(config: MilvusConfig) -> ServiceClientWrapper:
    client = MilvusClient(
        uri=config.uri,
        token=config.token or '',
        db_name=config.db_name,
        timeout=config.request_timeout_seconds,
    )
    return ServiceClientWrapper(client=client, service_name='milvus', healthcheck=client.list_collections)


@log_function_boundary()
def create_ollama_client(config: OllamaConfig) -> ServiceClientWrapper:
    client = OllamaClient(host=config.host, timeout=config.request_timeout_seconds)
    return ServiceClientWrapper(client=client, service_name='ollama', healthcheck=client.ps)


@log_function_boundary()
def create_langfuse_client(config: LangfuseConfig) -> ServiceClientWrapper | None:
    if not config.enabled:
        return None
    client = Langfuse(
        host=config.host,
        public_key=config.public_key,
        secret_key=config.secret_key,
        timeout=config.request_timeout_seconds,
        environment=config.environment,
        release=config.release,
        tracing_enabled=True,
    )
    return ServiceClientWrapper(client=client, service_name='langfuse', healthcheck=client.auth_check, close_fn=client.flush)


@log_function_boundary()
def create_nats_client(config: NatsConfig) -> NatsConnectionBuilder:
    return NatsConnectionBuilder(
        servers=list(config.servers),
        name=config.name,
        connect_timeout_seconds=config.connect_timeout_seconds,
        max_reconnect_attempts=config.max_reconnect_attempts,
        user=config.user,
        password=config.password,
        token=config.token,
        creds_file=config.creds_file,
    )


@log_function_boundary()
def close_service_clients(clients: Iterable[Any]) -> None:
    for client in clients:
        if client is None:
            continue
        close_method = getattr(client, 'close', None)
        if callable(close_method):
            close_method()


@log_function_boundary()
def _postgres_url(config: PostgresConfig) -> str | URL:
    if config.dsn:
        return make_url(config.dsn)
    return URL.create(
        'postgresql+psycopg',
        username=config.user or '',
        password=config.password or '',
        host=config.host or 'localhost',
        port=config.port,
        database=config.db or '',
    )


@log_function_boundary()
def _sqlite_url(config: SqliteConfig) -> str:
    if config.path == ':memory:':
        return 'sqlite:///:memory:'
    path = Path(config.path)
    database_path = path if path.is_absolute() else path
    if config.readonly:
        return f'sqlite:///file:{database_path.as_posix()}?mode=ro&uri=true'
    return f'sqlite:///{database_path.as_posix()}'


@log_function_boundary()
def _configure_sqlite_engine(client: Any, config: SqliteConfig) -> None:

    @event.listens_for(client, 'connect')
    @log_function_boundary()
    def _apply_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute(f'PRAGMA busy_timeout = {config.busy_timeout_ms}')
            if config.enable_wal:
                cursor.execute('PRAGMA journal_mode=WAL')
        finally:
            cursor.close()


@log_function_boundary()
def _check_postgres(client: Any) -> Any:
    with client.connect() as connection:
        return connection.exec_driver_sql('SELECT 1')


@log_function_boundary()
async def _close_async_client(client: Any) -> None:
    drain_method = getattr(client, 'drain', None)
    if callable(drain_method):
        drain_result = drain_method()
        if inspect.isawaitable(drain_result):
            await drain_result
            return
    close_method = getattr(client, 'close', None)
    if callable(close_method):
        close_result = close_method()
        if inspect.isawaitable(close_result):
            await close_result


@log_function_boundary()
def _error_type(exc: Exception) -> str:
    name = exc.__class__.__name__
    characters: list[str] = []
    for index, char in enumerate(name):
        if char.isupper() and index > 0:
            characters.append('_')
        characters.append(char.lower())
    return ''.join(characters) or 'error'
