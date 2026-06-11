from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field
import inspect
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from langfuse import Langfuse
from minio import Minio
from nats import connect as nats_connect
from ollama import Client as OllamaClient
from pymilvus import MilvusClient
from sqlalchemy import create_engine, event

from .config import KeycloakConfig, NatsConfig, PostgresConfig, Settings, SqliteConfig
from .keycloak import KeycloakAuthService

Builder = Callable[[Any], Any]
HealthCheck = Callable[[], Any]


@dataclass
class ServiceClientWrapper:
    client: Any
    healthcheck: HealthCheck
    close_fn: Callable[[], Any] | None = None

    def ping(self) -> Any:
        return self.healthcheck()

    def check(self) -> Any:
        return self.ping()

    def close(self) -> Any:
        if self.close_fn is not None:
            return self.close_fn()
        close_method = getattr(self.client, "close", None)
        if callable(close_method):
            return close_method()
        return None

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
    def connect_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "servers": self.servers,
            "name": self.name,
            "connect_timeout": self.connect_timeout_seconds,
            "max_reconnect_attempts": self.max_reconnect_attempts,
        }
        if self.user is not None:
            kwargs["user"] = self.user
        if self.password is not None:
            kwargs["password"] = self.password
        if self.token is not None:
            kwargs["token"] = self.token
        if self.creds_file is not None:
            kwargs["user_credentials"] = self.creds_file
        return kwargs

    async def connect(self) -> Any:
        result = self._connect_fn(**self.connect_kwargs)
        if inspect.isawaitable(result):
            return await result
        return result

    async def ping(self) -> Any:
        client = await self.connect()
        try:
            flush_method = getattr(client, "flush", None)
            if callable(flush_method):
                await flush_method()
            return client
        finally:
            await _close_async_client(client)

    async def check(self) -> Any:
        return await self.ping()


@dataclass
class ServiceFactoryRegistry:
    settings: Settings
    keycloak_builder: Builder | None = None
    postgres_builder: Builder | None = None
    sqlite_builder: Builder | None = None
    minio_builder: Builder | None = None
    milvus_builder: Builder | None = None
    ollama_builder: Builder | None = None
    langfuse_builder: Builder | None = None
    nats_builder: Builder | None = None

    def __post_init__(self) -> None:
        self._builders = {
            "keycloak": (self.keycloak_builder or self._build_keycloak_client, self.settings.keycloak),
            "minio": (self.minio_builder or self._build_minio_client, self.settings.minio),
            "milvus": (self.milvus_builder or self._build_milvus_client, self.settings.milvus),
            "ollama": (self.ollama_builder or self._build_ollama_client, self.settings.ollama),
            "langfuse": (self.langfuse_builder or self._build_langfuse_client, self.settings.langfuse),
            "nats": (self.nats_builder or self._build_nats_client, self.settings.nats),
        }
        if self.settings.postgres is not None:
            self._builders["postgres"] = (self.postgres_builder or self._build_postgres_client, self.settings.postgres)
        if self.settings.sqlite is not None:
            self._builders["sqlite"] = (self.sqlite_builder or self._build_sqlite_client, self.settings.sqlite)
        self._clients: dict[str, Any] = {}

    def create_client(self, service_name: str) -> Any:
        if service_name not in self._builders:
            raise KeyError(f"Unsupported service: {service_name}")
        if service_name not in self._clients:
            builder, config = self._builders[service_name]
            built_client = builder(config)
            self._clients[service_name] = self._wrap_client(service_name, built_client)
        return self._clients[service_name]

    def create_clients(self, services: Iterable[str]) -> dict[str, Any]:
        return {service_name: self.create_client(service_name) for service_name in services}

    def close_all(self) -> None:
        for client in self._clients.values():
            close_method = getattr(client, "close", None)
            if callable(close_method):
                close_method()

    def _wrap_client(self, service_name: str, client: Any) -> Any:
        if client is None or isinstance(client, (ServiceClientWrapper, NatsConnectionBuilder)):
            return client
        if service_name == "keycloak":
            return ServiceClientWrapper(client=client, healthcheck=client.fetch_access_token)
        if service_name == "postgres":
            return ServiceClientWrapper(client=client, healthcheck=lambda: _check_postgres(client), close_fn=client.dispose)
        if service_name == "sqlite":
            return ServiceClientWrapper(client=client, healthcheck=lambda: _check_postgres(client), close_fn=client.dispose)
        if service_name == "minio":
            return ServiceClientWrapper(client=client, healthcheck=client.list_buckets)
        if service_name == "milvus":
            return ServiceClientWrapper(client=client, healthcheck=client.list_collections)
        if service_name == "ollama":
            return ServiceClientWrapper(client=client, healthcheck=client.ps)
        if service_name == "langfuse":
            return ServiceClientWrapper(client=client, healthcheck=client.auth_check, close_fn=client.flush)
        if service_name == "nats":
            return client
        raise KeyError(f"Unsupported service: {service_name}")

    def _build_keycloak_client(self, _: KeycloakConfig) -> ServiceClientWrapper:
        client = KeycloakAuthService(self.settings)
        return ServiceClientWrapper(client=client, healthcheck=client.fetch_access_token)

    def _build_postgres_client(self, config: PostgresConfig) -> ServiceClientWrapper:
        client = create_engine(
            _postgres_url(config),
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
            connect_args={
                "connect_timeout": config.connect_timeout_seconds,
                "sslmode": config.sslmode,
            },
        )
        return ServiceClientWrapper(
            client=client,
            healthcheck=lambda: _check_postgres(client),
            close_fn=client.dispose,
        )

    def _build_sqlite_client(self, config: SqliteConfig) -> ServiceClientWrapper:
        client = create_engine(
            _sqlite_url(config),
            connect_args={
                "timeout": config.busy_timeout_ms / 1000,
                "check_same_thread": False,
            },
        )
        _configure_sqlite_engine(client, config)
        return ServiceClientWrapper(
            client=client,
            healthcheck=lambda: _check_postgres(client),
            close_fn=client.dispose,
        )

    def _build_minio_client(self, config) -> ServiceClientWrapper:
        client = Minio(
            config.endpoint,
            access_key=config.access_key,
            secret_key=config.secret_key,
            secure=config.secure,
            region=config.region,
            cert_check=config.secure,
        )
        return ServiceClientWrapper(client=client, healthcheck=client.list_buckets)

    def _build_milvus_client(self, config) -> ServiceClientWrapper:
        client = MilvusClient(
            uri=config.uri,
            token=config.token or "",
            db_name=config.db_name,
            timeout=config.request_timeout_seconds,
        )
        return ServiceClientWrapper(client=client, healthcheck=client.list_collections)

    def _build_ollama_client(self, config) -> ServiceClientWrapper:
        client = OllamaClient(host=config.host, timeout=config.request_timeout_seconds)
        return ServiceClientWrapper(client=client, healthcheck=client.ps)

    def _build_langfuse_client(self, config) -> ServiceClientWrapper | None:
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
        return ServiceClientWrapper(client=client, healthcheck=client.auth_check, close_fn=client.flush)

    def _build_nats_client(self, config: NatsConfig) -> NatsConnectionBuilder:
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


def _postgres_url(config: PostgresConfig) -> str:
    if config.dsn:
        return config.dsn
    username = quote_plus(config.user or "")
    password = quote_plus(config.password or "")
    host = config.host or "localhost"
    port = config.port
    database = config.db or ""
    return f"postgresql://{username}:***@{host}:{port}/{database}"


def _sqlite_url(config: SqliteConfig) -> str:
    if config.path == ":memory:":
        return "sqlite:///:memory:"

    path = Path(config.path)
    database_path = path if path.is_absolute() else path
    if config.readonly:
        return f"sqlite:///file:{database_path.as_posix()}?mode=ro&uri=true"
    return f"sqlite:///{database_path.as_posix()}"


def _configure_sqlite_engine(client: Any, config: SqliteConfig) -> None:
    @event.listens_for(client, "connect")
    def _apply_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute(f"PRAGMA busy_timeout = {config.busy_timeout_ms}")
            if config.enable_wal:
                cursor.execute("PRAGMA journal_mode=WAL")
        finally:
            cursor.close()


def _check_postgres(client: Any) -> Any:
    with client.connect() as connection:
        return connection.exec_driver_sql("SELECT 1")


async def _close_async_client(client: Any) -> None:
    drain_method = getattr(client, "drain", None)
    if callable(drain_method):
        drain_result = drain_method()
        if inspect.isawaitable(drain_result):
            await drain_result
            return
    close_method = getattr(client, "close", None)
    if callable(close_method):
        close_result = close_method()
        if inspect.isawaitable(close_result):
            await close_result
