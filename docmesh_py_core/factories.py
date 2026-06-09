from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from .config import Settings

Builder = Callable[[Any], Any]


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
            "keycloak": (self.keycloak_builder or (lambda config: config), self.settings.keycloak),
            "postgres": (self.postgres_builder or (lambda config: config), self.settings.postgres),
            "minio": (self.minio_builder or (lambda config: config), self.settings.minio),
            "milvus": (self.milvus_builder or (lambda config: config), self.settings.milvus),
            "ollama": (self.ollama_builder or (lambda config: config), self.settings.ollama),
            "langfuse": (self.langfuse_builder or (lambda config: config), self.settings.langfuse),
            "nats": (self.nats_builder or (lambda config: config), self.settings.nats),
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
