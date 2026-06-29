from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory
from unittest.mock import Mock

import pytest

from docmesh_py_core.config import load_settings
from docmesh_py_core.keycloak import (
    KeycloakAuthService,
    KeycloakTokenTemporaryError,
    TokenValidationError,
)


pytestmark = [pytest.mark.unit, pytest.mark.keycloak]


def _settings(*, audience: str | None = None):
    env = {
        "KEYCLOAK_URL": "https://kc.example.com",
        "KEYCLOAK_REALM": "docmesh",
        "KEYCLOAK_CLIENT_ID": "backend",
        "KEYCLOAK_CLIENT_SECRET": "client-secret",
        "KEYCLOAK_JWKS_CACHE_TTL_SECONDS": "5",
        "KEYCLOAK_PROVISIONING_ENABLED": "true",
        "KEYCLOAK_PROVISIONING_DRY_RUN": "false",
        "KEYCLOAK_ADMIN_CLIENT_SECRET": "admin-secret",
        "POSTGRES_DSN": "postgresql://user:***@db.example.com:5432/app",
        "MINIO_ENDPOINT": "minio.example.com:9000",
        "MINIO_ACCESS_KEY": "minio-access",
        "MINIO_SECRET_KEY": "minio-secret",
        "MILVUS_URI": "http://milvus.example.com:19530",
        "OLLAMA_HOST": "http://ollama.example.com:11434",
        "LANGFUSE_HOST": "https://langfuse.example.com",
        "LANGFUSE_PUBLIC_KEY": "public-key",
        "LANGFUSE_SECRET_KEY": "secret-key",
        "NATS_SERVERS": "nats://n1:4222",
        "KEYCLOAK_REALM_ROLES": "reader,writer",
        "KEYCLOAK_CLIENT_ROLES": "admin",
    }
    if audience is not None:
        env["KEYCLOAK_AUDIENCE"] = audience
    return load_settings(env)


def _encode_hs256_jwt(claims: dict[str, object], secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}

    def _b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    signing_input = (
        f"{_b64url(json.dumps(header, separators=(',', ':')).encode('utf-8'))}."
        f"{_b64url(json.dumps(claims, separators=(',', ':')).encode('utf-8'))}"
    )
    signature = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url(signature)}"


def _encode_rs256_jwt(claims: dict[str, object]) -> tuple[str, dict[str, object]]:
    with TemporaryDirectory() as temp_dir:
        private_key_path = Path(temp_dir) / "private.pem"
        public_key_path = Path(temp_dir) / "public.pem"
        signing_input_path = Path(temp_dir) / "signing-input.txt"
        signature_path = Path(temp_dir) / "signature.bin"

        run(
            ["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(private_key_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        run(
            ["openssl", "rsa", "-pubout", "-in", str(private_key_path), "-out", str(public_key_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        modulus_output = run(
            ["openssl", "rsa", "-pubin", "-in", str(public_key_path), "-modulus", "-noout"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        modulus_hex = modulus_output.split("=", 1)[1]
        modulus = base64.urlsafe_b64encode(bytes.fromhex(modulus_hex)).rstrip(b"=").decode("ascii")
        exponent = base64.urlsafe_b64encode((65537).to_bytes(3, "big")).rstrip(b"=").decode("ascii")

        header = {"alg": "RS256", "typ": "JWT", "kid": "test-rs256-key"}
        signing_input = (
            f"{base64.urlsafe_b64encode(json.dumps(header, separators=(',', ':')).encode('utf-8')).rstrip(b'=').decode('ascii')}."
            f"{base64.urlsafe_b64encode(json.dumps(claims, separators=(',', ':')).encode('utf-8')).rstrip(b'=').decode('ascii')}"
        )
        signing_input_path.write_text(signing_input, encoding="utf-8")
        run(
            [
                "openssl",
                "dgst",
                "-sha256",
                "-sign",
                str(private_key_path),
                "-out",
                str(signature_path),
                str(signing_input_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        signature = base64.urlsafe_b64encode(signature_path.read_bytes()).rstrip(b"=").decode("ascii")
        token = f"{signing_input}.{signature}"
        jwks = {
            "keys": [
                {
                    "kty": "RSA",
                    "use": "sig",
                    "alg": "RS256",
                    "kid": "test-rs256-key",
                    "n": modulus,
                    "e": exponent,
                }
            ]
        }
        return token, jwks


def test_keycloak_auth_service_fetches_access_token_with_client_credentials():
    http_client = Mock()
    http_client.post.return_value = {
        "status_code": 200,
        "json": {
            "access_token": "access-token-value",
            "token_type": "Bearer",
            "expires_in": 300,
        },
    }

    auth = KeycloakAuthService(_settings(), http_client=http_client)

    token = auth.fetch_access_token()

    assert token.access_token == "access-token-value"
    assert token.token_type == "Bearer"
    assert token.expires_in == 300
    http_client.post.assert_called_once_with(
        "https://kc.example.com/realms/docmesh/protocol/openid-connect/token",
        data={
            "grant_type": "client_credentials",
            "client_id": "backend",
            "client_secret": "client-secret",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
        verify_ssl=True,
    )


def test_keycloak_auth_service_treats_server_errors_as_temporary():
    http_client = Mock()
    http_client.post.return_value = {
        "status_code": 503,
        "json": {"error_description": "token temporary outage"},
    }

    auth = KeycloakAuthService(_settings(), http_client=http_client)

    with pytest.raises(KeycloakTokenTemporaryError):
        auth.fetch_access_token()


def test_keycloak_auth_service_accepts_password_grant_credentials_from_function_parameters():
    http_client = Mock()
    http_client.post.return_value = {
        "status_code": 200,
        "json": {
            "access_token": "password-grant-token",
            "token_type": "Bearer",
            "expires_in": 300,
        },
    }
    settings = _settings()
    settings.keycloak.token_grant_type = "password"
    settings.keycloak.token_username = None
    settings.keycloak.token_password = None

    auth = KeycloakAuthService(settings, http_client=http_client)

    token = auth.fetch_access_token(username="alice", password="wonderland")

    assert token.access_token == "password-grant-token"
    http_client.post.assert_called_once_with(
        "https://kc.example.com/realms/docmesh/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "backend",
            "client_secret": "client-secret",
            "username": "alice",
            "password": "wonderland",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
        verify_ssl=True,
    )


def test_keycloak_auth_service_extracts_standard_user_info_and_roles():
    signing_key = "unit-test-signing-key-32-bytes-min"
    now = datetime.now(UTC)
    token = _encode_hs256_jwt(
        {
            "sub": "user-123",
            "preferred_username": "alice",
            "email": "alice@example.com",
            "given_name": "Alice",
            "family_name": "Kim",
            "name": "Alice Kim",
            "iss": "https://kc.example.com/realms/docmesh",
            "aud": "docmesh-api",
            "exp": int((now + timedelta(minutes=5)).timestamp()),
            "iat": int(now.timestamp()),
            "realm_access": {"roles": ["reader", "writer"]},
            "resource_access": {
                "backend": {"roles": ["admin"]},
                "other-client": {"roles": ["viewer"]},
            },
        },
        signing_key,
    )

    auth = KeycloakAuthService(
        _settings(audience="docmesh-api"),
        verification_key=signing_key,
        allowed_algorithms=["HS256"],
    )

    user = auth.extract_user_info(token)

    assert user.sub == "user-123"
    assert user.preferred_username == "alice"
    assert user.email == "alice@example.com"
    assert user.given_name == "Alice"
    assert user.family_name == "Kim"
    assert user.name == "Alice Kim"
    assert user.realm_roles == ["reader", "writer"]
    assert user.client_roles == {"backend": ["admin"], "other-client": ["viewer"]}
    assert user.claims["sub"] == "user-123"


def test_keycloak_auth_service_rejects_expired_not_yet_valid_or_invalid_audience_tokens():
    signing_key = "unit-test-signing-key-32-bytes-min"
    now = datetime.now(UTC)
    expired = _encode_hs256_jwt(
        {
            "sub": "user-123",
            "iss": "https://kc.example.com/realms/docmesh",
            "aud": "docmesh-api",
            "exp": int((now - timedelta(minutes=1)).timestamp()),
        },
        signing_key,
    )
    not_yet_valid = _encode_hs256_jwt(
        {
            "sub": "user-123",
            "iss": "https://kc.example.com/realms/docmesh",
            "aud": "docmesh-api",
            "exp": int((now + timedelta(minutes=5)).timestamp()),
            "nbf": int((now + timedelta(minutes=1)).timestamp()),
        },
        signing_key,
    )
    wrong_audience = _encode_hs256_jwt(
        {
            "sub": "user-123",
            "iss": "https://kc.example.com/realms/docmesh",
            "aud": "other-audience",
            "exp": int((now + timedelta(minutes=5)).timestamp()),
        },
        signing_key,
    )

    auth = KeycloakAuthService(
        _settings(audience="docmesh-api"),
        verification_key=signing_key,
        allowed_algorithms=["HS256"],
    )

    with pytest.raises(TokenValidationError):
        auth.extract_user_info(expired)

    with pytest.raises(TokenValidationError):
        auth.extract_user_info(not_yet_valid)

    with pytest.raises(TokenValidationError):
        auth.extract_user_info(wrong_audience)


def test_keycloak_auth_service_validates_rs256_tokens_against_jwks():
    now = datetime.now(UTC)
    token, jwks = _encode_rs256_jwt(
        {
            "sub": "user-rs256",
            "preferred_username": "bob",
            "iss": "https://kc.example.com/realms/docmesh",
            "aud": "docmesh-api",
            "exp": int((now + timedelta(minutes=5)).timestamp()),
            "realm_access": {"roles": ["reader"]},
            "resource_access": {"backend": {"roles": ["admin"]}},
        }
    )

    auth = KeycloakAuthService(
        _settings(audience="docmesh-api"),
        http_client=Mock(),
        allowed_algorithms=["RS256"],
    )
    auth._jwks_cache = jwks

    user = auth.extract_user_info(token)

    assert user.sub == "user-rs256"
    assert user.preferred_username == "bob"
    assert user.realm_roles == ["reader"]
    assert user.client_roles == {"backend": ["admin"]}


def test_keycloak_auth_service_refreshes_jwks_after_cache_ttl_expires():
    now = datetime.now(UTC)
    token, jwks = _encode_rs256_jwt(
        {
            "sub": "ttl-user",
            "iss": "https://kc.example.com/realms/docmesh",
            "aud": "docmesh-api",
            "exp": int((now + timedelta(minutes=5)).timestamp()),
        }
    )
    http_client = Mock()
    http_client.get.return_value = {"status_code": 200, "json": jwks}
    current_time = Mock(side_effect=[100.0, 106.0, 106.0])

    auth = KeycloakAuthService(
        _settings(audience="docmesh-api"),
        http_client=http_client,
        allowed_algorithms=["RS256"],
        current_time=current_time,
    )

    auth.extract_user_info(token)
    auth.extract_user_info(token)

    assert http_client.get.call_count == 2



def test_keycloak_auth_service_refreshes_jwks_when_kid_rotates():
    now = datetime.now(UTC)
    token_one, jwks_one = _encode_rs256_jwt(
        {
            "sub": "rotation-one",
            "iss": "https://kc.example.com/realms/docmesh",
            "aud": "docmesh-api",
            "exp": int((now + timedelta(minutes=5)).timestamp()),
        }
    )
    token_two, jwks_two = _encode_rs256_jwt(
        {
            "sub": "rotation-two",
            "iss": "https://kc.example.com/realms/docmesh",
            "aud": "docmesh-api",
            "exp": int((now + timedelta(minutes=5)).timestamp()),
        }
    )
    http_client = Mock()
    http_client.get.side_effect = [
        {"status_code": 200, "json": jwks_one},
        {"status_code": 200, "json": jwks_two},
    ]

    auth = KeycloakAuthService(
        _settings(audience="docmesh-api"),
        http_client=http_client,
        allowed_algorithms=["RS256"],
    )

    user_one = auth.extract_user_info(token_one)
    user_two = auth.extract_user_info(token_two)

    assert user_one.sub == "rotation-one"
    assert user_two.sub == "rotation-two"
    assert http_client.get.call_count == 2
