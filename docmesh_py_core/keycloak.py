from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from .config import Settings
from .security import mask_sensitive_value


class KeycloakAdminClient(Protocol):
    def ensure_realm(self, config) -> str: ...

    def ensure_client(self, config) -> str: ...

    def ensure_realm_role(self, realm: str, role_name: str) -> str: ...

    def ensure_client_role(self, realm: str, client_id: str, role_name: str) -> str: ...


@dataclass
class ProvisioningResult:
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)
    planned: list[str] = field(default_factory=list)
    dry_run: bool = False


class KeycloakProvisioner:
    def __init__(self, settings: Settings, *, admin_client: KeycloakAdminClient) -> None:
        self.settings = settings
        self.admin_client = admin_client

    def provision(self) -> ProvisioningResult:
        config = self.settings.keycloak
        result = ProvisioningResult(dry_run=config.provisioning_dry_run)
        operations = [
            (f"realm:{config.realm}", lambda: self.admin_client.ensure_realm(config)),
            (f"client:{config.client_id}", lambda: self.admin_client.ensure_client(config)),
        ]
        operations.extend(
            (f"realm-role:{role}", lambda role=role: self.admin_client.ensure_realm_role(config.realm, role))
            for role in config.realm_roles
        )
        operations.extend(
            (
                f"client-role:{config.client_id}/{role}",
                lambda role=role: self.admin_client.ensure_client_role(config.realm, config.client_id, role),
            )
            for role in config.client_roles
        )

        if config.provisioning_dry_run:
            result.planned = [name for name, _ in operations]
            return result

        for item_name, operation in operations:
            try:
                state = operation()
            except Exception as exc:
                result.failed.append((item_name, mask_sensitive_value(str(exc)) or "***"))
                continue

            if state == "created":
                result.created.append(item_name)
            elif state == "updated":
                result.updated.append(item_name)
            else:
                result.unchanged.append(item_name)

        return result
