from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote_plus

try:
    from langfuse import Langfuse
except ModuleNotFoundError:  # pragma: no cover - optional dependency in unit-test env
    Langfuse = None

try:
    from minio import Minio
except ModuleNotFoundError:  # pragma: no cover - optional dependency in unit-test env
    Minio = None

try:
    from nats import connect as nats_connect
except ModuleNotFoundError:  # pragma: no cover - optional dependency in unit-test env
    nats_connect = None

try:
    from ollama import Client as OllamaClient
except ModuleNotFoundError:  # pragma: no cover - optional dependency in unit-test env
    OllamaClient = None

try:
    from pymilvus import MilvusClient
except ModuleNotFoundError:  # pragma: no cover - optional dependency in unit-test env
    MilvusClient = None

try:
    from sqlalchemy import create_engine
except ModuleNotFoundError:  # pragma: no cover - optional dependency in unit-test env
    create_engine = None

from .config import KeycloakConfig, NatsConfig, PostgresConfig, Settings
from .keycloak import KeycloakAuthService

Builder = Callable[[Any], Any]


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
    _connect_fn: Callable[..., Awaitable[Any]] | None = field(default=nats_connect, repr=False, compare=False)

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
        if self._connect_fn is None:
            raise ModuleNotFoundError("nats dependency is not installed")
        return await self._connect_fn(**self.connect_kwargs)


@dataclass
class ServiceFactoryRegistry:
    settings: Settings
    keycloak_builder: Builder | None = None
    postgres_builder: Builder | None = None
    minio_builder: Builder | None = None
    milvus_builder: Builder | None = None
    ollama_builder: Builder | None = None
    langfuse_builder: Builder | None = None
    nats_builder: Builder | None = None

    def __post_init__(self) -> None:
        self._builders = {
            "keycloak": (self.keycloak_builder or self._build_keycloak_client, self.settings.keycloak),
            "postgres": (self.postgres_builder or self._build_postgres_client, self.settings.postgres),
            "minio": (self.minio_builder or self._build_minio_client, self.settings.minio),
            "milvus": (self.milvus_builder or self._build_milvus_client, self.settings.milvus),
            "ollama": (self.ollama_builder or self._build_ollama_client, self.settings.ollama),
            "langfuse": (self.langfuse_builder or self._build_langfuse_client, self.settings.langfuse),
            "nats": (self.nats_builder or self._build_nats_client, self.settings.nats),
        }
        self._clients: dict[str, Any] = {}

    def create_client(self, service_name: str) -> Any:
        if service_name not in self._builders:
            raise KeyError(f"Unsupported service: {service_name}")
        if service_name not in self._clients:
            builder, config = self._builders[service_name]
            self._clients[service_name] = builder(config)
        return self._clients[service_name]

    def create_clients(self, services: Iterable[str]) -> dict[str, Any]:
        return {service_name: self.create_client(service_name) for service_name in services}

    def close_all(self) -> None:
        for client in self._clients.values():
            close_method = getattr(client, "close", None)
            if callable(close_method):
                close_method()

    def _build_keycloak_client(self, _: KeycloakConfig) -> KeycloakAuthService:
        return KeycloakAuthService(self.settings)

    def _build_postgres_client(self, config: PostgresConfig) -> Any:
        if create_engine is None:
            raise ModuleNotFoundError("sqlalchemy dependency is not installed")
        return create_engine(
            _postgres_url(config),
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
            connect_args={
                "connect_timeout": config.connect_timeout_seconds,
                "sslmode": config.sslmode,
            },
        )

    def _build_minio_client(self, config) -> Any:
        if Minio is None:
            raise ModuleNotFoundError("minio dependency is not installed")
        return Minio(
            config.endpoint,
            access_key=config.access_key,
            secret_key=config.secret_key,
            secure=config.secure,
            region=config.region,
            cert_check=config.secure,
        )

    def _build_milvus_client(self, config) -> Any:
        if MilvusClient is None:
            raise ModuleNotFoundError("pymilvus dependency is not installed")
        return MilvusClient(
            uri=config.uri,
            token=config.token or "",
            db_name=config.db_name,
            timeout=config.request_timeout_seconds,
        )

    def _build_ollama_client(self, config) -> Any:
        if OllamaClient is None:
            raise ModuleNotFoundError("ollama dependency is not installed")
        return OllamaClient(host=config.host, timeout=config.request_timeout_seconds)

    def _build_langfuse_client(self, config) -> Any:
        if not config.enabled:
            return None
        if Langfuse is None:
            raise ModuleNotFoundError("langfuse dependency is not installed")
        return Langfuse(
            host=config.host,
            public_key=config.public_key,
            secret_key=config.secret_key,
            timeout=config.request_timeout_seconds,
            environment=config.environment,
            release=config.release,
            tracing_enabled=True,
        )

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
    return f"postgresql://{username}:{password}@{host}:{port}/{database}"
