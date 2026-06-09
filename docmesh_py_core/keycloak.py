from __future__ import annotations

import base64
import hashlib
import hmac
import json
import ssl
import time
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import ConfigError, Settings
from .security import mask_sensitive_value


class KeycloakAdminClient(Protocol):
    def ensure_realm(self, config) -> str: ...

    def ensure_client(self, config) -> str: ...

    def ensure_realm_role(self, realm: str, role_name: str) -> str: ...

    def ensure_client_role(self, realm: str, client_id: str, role_name: str) -> str: ...


class KeycloakHttpClient(Protocol):
    def post(
        self,
        url: str,
        *,
        data: dict[str, str],
        headers: dict[str, str],
        timeout: int,
        verify_ssl: bool,
    ) -> dict[str, Any]: ...


@dataclass
class ProvisioningResult:
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)
    planned: list[str] = field(default_factory=list)
    dry_run: bool = False


@dataclass(frozen=True)
class AccessTokenResult:
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str | None = None
    scope: str | None = None


@dataclass(frozen=True)
class AuthenticatedUser:
    sub: str
    preferred_username: str | None
    email: str | None
    given_name: str | None
    family_name: str | None
    name: str | None
    realm_roles: list[str]
    client_roles: dict[str, list[str]]
    claims: dict[str, Any]


class KeycloakError(RuntimeError):
    pass


class KeycloakTokenError(KeycloakError):
    pass


class KeycloakTokenConfigurationError(KeycloakTokenError):
    pass


class KeycloakTokenAuthenticationError(KeycloakTokenError):
    pass


class KeycloakTokenTemporaryError(KeycloakTokenError):
    pass


class TokenValidationError(KeycloakError):
    pass


class _UrllibKeycloakHttpClient:
    def post(
        self,
        url: str,
        *,
        data: dict[str, str],
        headers: dict[str, str],
        timeout: int,
        verify_ssl: bool,
    ) -> dict[str, Any]:
        encoded = urlencode(data).encode("utf-8")
        request = Request(url, data=encoded, headers=headers, method="POST")
        context = None
        if url.startswith("https://"):
            context = ssl.create_default_context()
            if not verify_ssl:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE

        try:
            with urlopen(request, timeout=timeout, context=context) as response:
                body = response.read().decode("utf-8")
                return {
                    "status_code": getattr(response, "status", response.getcode()),
                    "json": _safe_json_loads(body),
                    "text": body,
                }
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            return {
                "status_code": exc.code,
                "json": _safe_json_loads(body),
                "text": body,
            }
        except URLError as exc:
            raise KeycloakTokenTemporaryError(mask_sensitive_value(str(exc.reason)) or "temporary network failure") from exc


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


class KeycloakAuthService:
    def __init__(
        self,
        settings: Settings,
        *,
        http_client: KeycloakHttpClient | None = None,
        verification_key: str | None = None,
        allowed_algorithms: list[str] | None = None,
    ) -> None:
        self.settings = settings
        self.http_client = http_client or _UrllibKeycloakHttpClient()
        self.verification_key = verification_key
        self.allowed_algorithms = allowed_algorithms or ["HS256"]

    def fetch_access_token(self, *, scope: str | None = None) -> AccessTokenResult:
        config = self.settings.keycloak
        payload = {
            "grant_type": config.token_grant_type,
            "client_id": config.client_id,
        }
        if config.client_secret:
            payload["client_secret"] = config.client_secret
        effective_scope = scope or config.token_scope
        if effective_scope:
            payload["scope"] = effective_scope
        if config.token_grant_type == "password":
            if not (config.token_username and config.token_password):
                raise KeycloakTokenConfigurationError("Password grant requires KEYCLOAK_TOKEN_USERNAME and KEYCLOAK_TOKEN_PASSWORD")
            payload["username"] = config.token_username
            payload["password"] = config.token_password

        response = self.http_client.post(
            self.token_endpoint,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=config.request_timeout_seconds,
            verify_ssl=config.verify_ssl,
        )
        status_code = int(response.get("status_code", 0))
        body = response.get("json")
        if not isinstance(body, dict):
            body = {}

        if 200 <= status_code < 300:
            access_token = body.get("access_token")
            token_type = body.get("token_type")
            expires_in = body.get("expires_in")
            if not access_token or not token_type or expires_in is None:
                raise KeycloakTokenError("Keycloak token response is missing required fields")
            return AccessTokenResult(
                access_token=access_token,
                token_type=token_type,
                expires_in=int(expires_in),
                refresh_token=body.get("refresh_token"),
                scope=body.get("scope"),
            )

        description = _mask_error_detail(body.get("error_description") or body.get("error") or response.get("text") or "token request failed")
        if status_code in {400, 401, 403}:
            raise KeycloakTokenAuthenticationError(description)
        if status_code in {408, 429} or status_code >= 500:
            raise KeycloakTokenTemporaryError(description)
        raise KeycloakTokenError(description)

    def extract_user_info(self, token: str) -> AuthenticatedUser:
        raw_token = _strip_bearer_prefix(token)
        header, claims, signature, signing_input = _split_jwt(raw_token)
        algorithm = header.get("alg")
        if algorithm not in self.allowed_algorithms:
            raise TokenValidationError(f"Unsupported JWT algorithm: {algorithm}")
        self._verify_signature(algorithm, signing_input, signature)
        self._validate_registered_claims(claims)

        subject = claims.get("sub") or claims.get("jti")
        if not subject:
            raise TokenValidationError("JWT is missing subject information")

        realm_access = claims.get("realm_access") or {}
        resource_access = claims.get("resource_access") or {}
        realm_roles = _normalize_roles(realm_access.get("roles")) if isinstance(realm_access, dict) else []
        client_roles: dict[str, list[str]] = {}
        if isinstance(resource_access, dict):
            for client_name, client_claims in resource_access.items():
                if isinstance(client_claims, dict):
                    roles = _normalize_roles(client_claims.get("roles"))
                    if roles:
                        client_roles[str(client_name)] = roles

        return AuthenticatedUser(
            sub=str(subject),
            preferred_username=_optional_str(claims.get("preferred_username")),
            email=_optional_str(claims.get("email")),
            given_name=_optional_str(claims.get("given_name")),
            family_name=_optional_str(claims.get("family_name")),
            name=_optional_str(claims.get("name")),
            realm_roles=realm_roles,
            client_roles=client_roles,
            claims=claims,
        )

    @property
    def issuer(self) -> str:
        return f"{self.settings.keycloak.url.rstrip('/')}/realms/{self.settings.keycloak.realm}"

    @property
    def token_endpoint(self) -> str:
        return f"{self.issuer}/protocol/openid-connect/token"

    def _verify_signature(self, algorithm: str | None, signing_input: bytes, signature: bytes) -> None:
        if algorithm == "HS256":
            if self.verification_key is None:
                raise TokenValidationError("Verification key is required for HS256 token validation")
            expected = hmac.new(
                self.verification_key.encode("utf-8"),
                signing_input,
                hashlib.sha256,
            ).digest()
            if not hmac.compare_digest(expected, signature):
                raise TokenValidationError("JWT signature validation failed")
            return
        raise TokenValidationError(f"Unsupported JWT algorithm: {algorithm}")

    def _validate_registered_claims(self, claims: dict[str, Any]) -> None:
        issuer = claims.get("iss")
        if issuer != self.issuer:
            raise TokenValidationError("JWT issuer validation failed")

        exp = claims.get("exp")
        if exp is None:
            raise TokenValidationError("JWT expiration claim is required")
        try:
            expires_at = float(exp)
        except (TypeError, ValueError) as exc:
            raise TokenValidationError("JWT expiration claim is invalid") from exc
        if expires_at <= time.time():
            raise TokenValidationError("JWT has expired")

        expected_audience = self.settings.keycloak.audience
        if expected_audience:
            audience = claims.get("aud")
            if isinstance(audience, str):
                audiences = [audience]
            elif isinstance(audience, list):
                audiences = [str(item) for item in audience]
            else:
                audiences = []
            if expected_audience not in audiences:
                raise TokenValidationError("JWT audience validation failed")


def _strip_bearer_prefix(token: str) -> str:
    stripped = token.strip()
    if stripped.lower().startswith("bearer "):
        return stripped[7:].strip()
    return stripped


def _split_jwt(token: str) -> tuple[dict[str, Any], dict[str, Any], bytes, bytes]:
    parts = token.split(".")
    if len(parts) != 3:
        raise TokenValidationError("JWT must contain header, payload, and signature")
    header_segment, payload_segment, signature_segment = parts
    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    try:
        header = json.loads(_b64url_decode(header_segment))
        claims = json.loads(_b64url_decode(payload_segment))
        signature = _b64url_decode_bytes(signature_segment)
    except Exception as exc:
        raise TokenValidationError("JWT is malformed") from exc
    if not isinstance(header, dict) or not isinstance(claims, dict):
        raise TokenValidationError("JWT is malformed")
    return header, claims, signature, signing_input


def _b64url_decode(segment: str) -> str:
    return _b64url_decode_bytes(segment).decode("utf-8")


def _b64url_decode_bytes(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(f"{segment}{padding}")


def _normalize_roles(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _optional_str(value: Any) -> str | None:
    return str(value) if value is not None else None


def _mask_error_detail(detail: Any) -> str:
    masked = mask_sensitive_value(str(detail)) if detail is not None else None
    return masked or "***"


def _safe_json_loads(text: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None
