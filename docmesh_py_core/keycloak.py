from __future__ import annotations
import json
import logging
import ssl
import time
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import jwt
from jwt import algorithms
from jwt.exceptions import InvalidAlgorithmError, InvalidAudienceError, InvalidIssuerError, InvalidTokenError, MissingRequiredClaimError
from .config import KeycloakConfig
from .observability import build_service_log_event
from .retry import retry_call
from .security import mask_sensitive_value
from .function_logging import log_function_boundary

class KeycloakAdminClient(Protocol):

    def ensure_realm(self, config) -> str:
        ...

    def ensure_client(self, config) -> str:
        ...

    def ensure_realm_role(self, realm: str, role_name: str) -> str:
        ...

    def ensure_client_role(self, realm: str, client_id: str, role_name: str) -> str:
        ...

class KeycloakHttpClient(Protocol):

    def post(self, url: str, *, data: dict[str, str], headers: dict[str, str], timeout: int, verify_ssl: bool) -> dict[str, Any]:
        ...

    def get(self, url: str, *, headers: dict[str, str] | None=None, timeout: int, verify_ssl: bool) -> dict[str, Any]:
        ...

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

    @log_function_boundary()
    def post(self, url: str, *, data: dict[str, str], headers: dict[str, str], timeout: int, verify_ssl: bool) -> dict[str, Any]:
        encoded = urlencode(data).encode('utf-8')
        request = Request(url, data=encoded, headers=headers, method='POST')
        context = _build_ssl_context(url, verify_ssl)
        try:
            with urlopen(request, timeout=timeout, context=context) as response:
                body = response.read().decode('utf-8')
                return {'status_code': getattr(response, 'status', response.getcode()), 'json': _safe_json_loads(body), 'text': body}
        except HTTPError as exc:
            body = exc.read().decode('utf-8', errors='replace')
            return {'status_code': exc.code, 'json': _safe_json_loads(body), 'text': body}
        except URLError as exc:
            raise KeycloakTokenTemporaryError(mask_sensitive_value(str(exc.reason)) or 'temporary network failure') from exc

    @log_function_boundary()
    def get(self, url: str, *, headers: dict[str, str] | None=None, timeout: int, verify_ssl: bool) -> dict[str, Any]:
        request = Request(url, headers=headers or {}, method='GET')
        context = _build_ssl_context(url, verify_ssl)
        try:
            with urlopen(request, timeout=timeout, context=context) as response:
                body = response.read().decode('utf-8')
                return {'status_code': getattr(response, 'status', response.getcode()), 'json': _safe_json_loads(body), 'text': body}
        except HTTPError as exc:
            body = exc.read().decode('utf-8', errors='replace')
            return {'status_code': exc.code, 'json': _safe_json_loads(body), 'text': body}
        except URLError as exc:
            raise KeycloakTokenTemporaryError(mask_sensitive_value(str(exc.reason)) or 'temporary network failure') from exc

class KeycloakProvisioner:

    @log_function_boundary()
    def __init__(self, config: KeycloakConfig, *, admin_client: KeycloakAdminClient) -> None:
        self.config = config
        self.admin_client = admin_client

    @log_function_boundary()
    def provision(self) -> ProvisioningResult:
        config = self.config
        result = ProvisioningResult(dry_run=config.provisioning_dry_run)
        operations = [(f'realm:{config.realm}', lambda: self.admin_client.ensure_realm(config)), (f'client:{config.client_id}', lambda: self.admin_client.ensure_client(config))]
        operations.extend(((f'realm-role:{role}', lambda role=role: self.admin_client.ensure_realm_role(config.realm, role)) for role in config.realm_roles))
        operations.extend(((f'client-role:{config.client_id}/{role}', lambda role=role: self.admin_client.ensure_client_role(config.realm, config.client_id, role)) for role in config.client_roles))
        if config.provisioning_dry_run:
            result.planned = [name for name, _ in operations]
            return result
        for item_name, operation in operations:
            try:
                state = operation()
            except Exception as exc:
                result.failed.append((item_name, mask_sensitive_value(str(exc)) or '***'))
                continue
            if state == 'created':
                result.created.append(item_name)
            elif state == 'updated':
                result.updated.append(item_name)
            else:
                result.unchanged.append(item_name)
        return result

class KeycloakAuthService:

    @log_function_boundary()
    def __init__(self, config: KeycloakConfig, *, http_client: KeycloakHttpClient | None=None, verification_key: str | None=None, allowed_algorithms: list[str] | None=None, logger: logging.Logger | None=None, event_logger: callable | None=None, timer: callable=time.perf_counter, sleep: callable=time.sleep, current_time: callable=time.time) -> None:
        self.config = config
        self.http_client = http_client or _UrllibKeycloakHttpClient()
        self.verification_key = verification_key
        self.allowed_algorithms = allowed_algorithms or ['HS256']
        self.logger = logger or logging.getLogger(__name__)
        self.event_logger = event_logger or self._default_event_logger
        self.timer = timer
        self.sleep = sleep
        self.current_time = current_time
        self._jwks_cache: dict[str, Any] | None = None
        self._jwks_cache_loaded_at: float | None = None

    @log_function_boundary()
    def fetch_access_token(self, *, scope: str | None=None, username: str | None=None, password: str | None=None) -> AccessTokenResult:
        config = self.config
        payload = {'grant_type': config.token_grant_type, 'client_id': config.client_id}
        if config.client_secret:
            payload['client_secret'] = config.client_secret
        effective_scope = scope or config.token_scope
        if effective_scope:
            payload['scope'] = effective_scope
        if config.token_grant_type == 'password':
            if not (username and password):
                raise KeycloakTokenConfigurationError('Password grant requires username and password function arguments')
            payload['username'] = username
            payload['password'] = password
        max_attempts = config.max_retries + 1
        attempt_index = 0

        @log_function_boundary()
        def _request_token() -> AccessTokenResult:
            nonlocal attempt_index
            start = self.timer()
            try:
                response = self.http_client.post(self.token_endpoint, data=payload, headers={'Content-Type': 'application/x-www-form-urlencoded'}, timeout=config.request_timeout_seconds, verify_ssl=config.verify_ssl)
                result = self._parse_token_response(response)
            except Exception as exc:
                self._emit_token_event(outcome='temporary_error' if isinstance(exc, KeycloakTokenTemporaryError) else 'error', retry_count=attempt_index, latency_ms=int(round((self.timer() - start) * 1000)), error=str(exc))
                attempt_index += 1
                raise
            self._emit_token_event(outcome='success', retry_count=attempt_index, latency_ms=int(round((self.timer() - start) * 1000)))
            attempt_index += 1
            return result
        return retry_call(_request_token, retry_on=(KeycloakTokenTemporaryError,), max_attempts=max_attempts, sleep=self.sleep)

    @log_function_boundary()
    def extract_user_info(self, token: str) -> AuthenticatedUser:
        raw_token = _strip_bearer_prefix(token)
        claims = self._decode_and_validate_jwt(raw_token)
        subject = claims.get('sub') or claims.get('jti')
        if not subject:
            raise TokenValidationError('JWT is missing subject information')
        realm_access = claims.get('realm_access') or {}
        resource_access = claims.get('resource_access') or {}
        realm_roles = _normalize_roles(realm_access.get('roles')) if isinstance(realm_access, dict) else []
        client_roles: dict[str, list[str]] = {}
        if isinstance(resource_access, dict):
            for client_name, client_claims in resource_access.items():
                if isinstance(client_claims, dict):
                    roles = _normalize_roles(client_claims.get('roles'))
                    if roles:
                        client_roles[str(client_name)] = roles
        return AuthenticatedUser(sub=str(subject), preferred_username=_optional_str(claims.get('preferred_username')), email=_optional_str(claims.get('email')), given_name=_optional_str(claims.get('given_name')), family_name=_optional_str(claims.get('family_name')), name=_optional_str(claims.get('name')), realm_roles=realm_roles, client_roles=client_roles, claims=claims)

    @property
    @log_function_boundary()
    def issuer(self) -> str:
        return f"{self.config.url.rstrip('/')}/realms/{self.config.realm}"

    @property
    @log_function_boundary()
    def token_endpoint(self) -> str:
        return f'{self.issuer}/protocol/openid-connect/token'

    @property
    @log_function_boundary()
    def jwks_endpoint(self) -> str:
        return f'{self.issuer}/protocol/openid-connect/certs'

    @log_function_boundary()
    def _decode_and_validate_jwt(self, token: str) -> dict[str, Any]:
        try:
            header = jwt.get_unverified_header(token)
        except InvalidTokenError as exc:
            raise TokenValidationError('JWT is malformed') from exc
        algorithm = header.get('alg')
        if algorithm not in self.allowed_algorithms:
            raise TokenValidationError(f'Unsupported JWT algorithm: {algorithm}')
        key = self._resolve_verification_key(header)
        decode_kwargs = self._build_decode_kwargs()
        try:
            claims = jwt.decode(token, key=key, algorithms=[algorithm], **decode_kwargs)
        except InvalidAudienceError as exc:
            raise TokenValidationError('JWT audience validation failed') from exc
        except InvalidIssuerError as exc:
            raise TokenValidationError('JWT issuer validation failed') from exc
        except MissingRequiredClaimError as exc:
            if exc.claim == 'exp':
                raise TokenValidationError('JWT expiration claim is required') from exc
            raise TokenValidationError(f'JWT missing required claim: {exc.claim}') from exc
        except InvalidAlgorithmError as exc:
            raise TokenValidationError(f'Unsupported JWT algorithm: {algorithm}') from exc
        except InvalidTokenError as exc:
            detail = str(exc)
            if detail == 'Signature verification failed':
                if algorithm == 'RS256' and self._jwks_cache is not None:
                    refreshed_key = self._refresh_verification_key(header)
                    if refreshed_key is not None:
                        try:
                            claims = jwt.decode(token, key=refreshed_key, algorithms=[algorithm], **decode_kwargs)
                        except InvalidTokenError as retry_exc:
                            raise self._map_invalid_token_error(retry_exc) from retry_exc
                    else:
                        raise TokenValidationError('JWT signature validation failed') from exc
                else:
                    raise TokenValidationError('JWT signature validation failed') from exc
            else:
                raise self._map_invalid_token_error(exc) from exc
        if not isinstance(claims, dict):
            raise TokenValidationError('JWT is malformed')
        return claims

    @log_function_boundary()
    def _resolve_verification_key(self, header: dict[str, Any]) -> Any:
        algorithm = header.get('alg')
        if algorithm == 'HS256':
            if self.verification_key is None:
                raise TokenValidationError('Verification key is required for HS256 token validation')
            return self.verification_key
        if algorithm == 'RS256':
            return self._select_rs256_verification_key(header)
        raise TokenValidationError(f'Unsupported JWT algorithm: {algorithm}')

    @log_function_boundary()
    def _select_rs256_verification_key(self, header: dict[str, Any]) -> Any:
        jwk = self._select_jwk(header)
        return self._build_public_key_from_jwk(jwk)

    @log_function_boundary()
    def _select_jwk(self, header: dict[str, Any]) -> dict[str, Any]:
        kid = header.get('kid')
        if not kid:
            raise TokenValidationError('JWT header is missing key id')
        jwks = self._get_jwks()
        return self._find_jwk(jwks, kid)

    @log_function_boundary()
    def _get_jwks(self, *, force_refresh: bool=False) -> dict[str, Any]:
        ttl_seconds = self.config.jwks_cache_ttl_seconds
        if not force_refresh and self._jwks_cache is not None:
            if self._jwks_cache_loaded_at is None:
                return self._jwks_cache
            if ttl_seconds == 0 or self.current_time() - self._jwks_cache_loaded_at < ttl_seconds:
                return self._jwks_cache
        response = self.http_client.get(self.jwks_endpoint, headers={'Accept': 'application/json'}, timeout=self.config.request_timeout_seconds, verify_ssl=self.config.verify_ssl)
        status_code = int(response.get('status_code', 0))
        body = response.get('json')
        if status_code < 200 or status_code >= 300 or (not isinstance(body, dict)):
            detail = _mask_error_detail(response.get('text') or body or 'jwks fetch failed')
            raise TokenValidationError(f'Failed to load JWKS: {detail}')
        self._jwks_cache = body
        self._jwks_cache_loaded_at = self.current_time()
        return body

    @log_function_boundary()
    def _refresh_verification_key(self, header: dict[str, Any]) -> Any | None:
        refreshed_jwk = self._refresh_jwk_for_header(header)
        if refreshed_jwk is None:
            return None
        return self._build_public_key_from_jwk(refreshed_jwk)

    @log_function_boundary()
    def _refresh_jwk_for_header(self, header: dict[str, Any]) -> dict[str, Any] | None:
        kid = header.get('kid')
        if not kid:
            return None
        if self._jwks_cache is None:
            return None
        refreshed_jwks = self._get_jwks(force_refresh=True)
        return self._find_jwk(refreshed_jwks, kid)

    @log_function_boundary()
    def _find_jwk(self, jwks: dict[str, Any], kid: Any) -> dict[str, Any]:
        keys = jwks.get('keys')
        if not isinstance(keys, list):
            raise TokenValidationError('JWKS response is invalid')
        for candidate in keys:
            if isinstance(candidate, dict) and candidate.get('kid') == kid:
                return candidate
        raise TokenValidationError(f'No JWKS key found for kid: {kid}')

    @log_function_boundary()
    def _build_public_key_from_jwk(self, jwk: dict[str, Any]) -> Any:
        try:
            return algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
        except Exception as exc:
            raise TokenValidationError('JWKS RSA key is invalid') from exc

    @log_function_boundary()
    def _build_decode_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {'issuer': self.issuer, 'options': {'require': ['exp']}}
        expected_audience = self.config.audience
        if expected_audience:
            kwargs['audience'] = expected_audience
        else:
            kwargs['options']['verify_aud'] = False
        return kwargs

    @log_function_boundary()
    def _map_invalid_token_error(self, exc: InvalidTokenError) -> TokenValidationError:
        detail = str(exc)
        if detail == 'Signature verification failed':
            return TokenValidationError('JWT signature validation failed')
        if detail == 'Not enough segments':
            return TokenValidationError('JWT must contain header, payload, and signature')
        if detail == 'Token is missing the "exp" claim':
            return TokenValidationError('JWT expiration claim is required')
        if detail.startswith('Token is missing the '):
            missing_claim = detail.removeprefix('Token is missing the "').removesuffix('" claim')
            return TokenValidationError(f'JWT missing required claim: {missing_claim}')
        if detail == 'The token is not yet valid (nbf)':
            return TokenValidationError('JWT is not yet valid')
        if detail == 'The token is not yet valid (iat)':
            return TokenValidationError('JWT issued-at claim is invalid')
        if detail == 'Signature has expired':
            return TokenValidationError('JWT has expired')
        return TokenValidationError(detail or 'JWT is malformed')

    @log_function_boundary()
    def _parse_token_response(self, response: dict[str, Any]) -> AccessTokenResult:
        status_code = int(response.get('status_code', 0))
        body = response.get('json')
        if not isinstance(body, dict):
            body = {}
        if 200 <= status_code < 300:
            access_token = body.get('access_token')
            token_type = body.get('token_type')
            expires_in = body.get('expires_in')
            if not access_token or not token_type or expires_in is None:
                raise KeycloakTokenError('Keycloak token response is missing required fields')
            return AccessTokenResult(access_token=access_token, token_type=token_type, expires_in=int(expires_in), refresh_token=body.get('refresh_token'), scope=body.get('scope'))
        description = _mask_error_detail(body.get('error_description') or body.get('error') or response.get('text') or 'token request failed')
        if status_code in {400, 401, 403}:
            raise KeycloakTokenAuthenticationError(description)
        if status_code in {408, 429} or status_code >= 500:
            raise KeycloakTokenTemporaryError(description)
        raise KeycloakTokenError(description)

    @log_function_boundary()
    def _emit_token_event(self, *, outcome: str, retry_count: int, latency_ms: int, error: str | None=None) -> None:
        event = build_service_log_event(service='keycloak', operation='fetch_access_token', outcome=outcome, host=self.config.url, latency_ms=latency_ms, retry_count=retry_count, error=error)
        self.event_logger(event)

    @log_function_boundary()
    def _default_event_logger(self, event: dict[str, Any]) -> None:
        self.logger.info('service_event', extra={'service_event': event})

@log_function_boundary()
def _strip_bearer_prefix(token: str) -> str:
    stripped = token.strip()
    if stripped.lower().startswith('bearer '):
        return stripped[7:].strip()
    return stripped

@log_function_boundary()
def _build_ssl_context(url: str, verify_ssl: bool) -> ssl.SSLContext | None:
    if not url.startswith('https://'):
        return None
    context = ssl.create_default_context()
    if not verify_ssl:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    return context

@log_function_boundary()
def _normalize_roles(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]

@log_function_boundary()
def _optional_str(value: Any) -> str | None:
    return str(value) if value is not None else None

@log_function_boundary()
def _mask_error_detail(detail: Any) -> str:
    masked = mask_sensitive_value(str(detail)) if detail is not None else None
    return masked or '***'

@log_function_boundary()
def _safe_json_loads(text: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None
