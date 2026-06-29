# docmesh-py-core API Reference

이 문서는 `docmesh-py-core`의 **공개 API 레퍼런스**입니다.

- 사용 흐름을 먼저 알고 싶다면 [README](../README.md)를 읽으세요.
- 환경변수와 설정 규칙은 [설정 가이드](./config.md)를 참고하세요.
- 실제 통합 예시는 [examples.md](./examples.md)를 참고하세요.

## 1. Public imports

패키지 루트에서 바로 import 가능한 공개 API:

```python
from docmesh_py_core import (
    AccessTokenResult,
    AuthenticatedUser,
    ConfigError,
    HealthCheckError,
    KeycloakAuthService,
    KeycloakProvisioner,
    KeycloakTokenAuthenticationError,
    KeycloakTokenConfigurationError,
    KeycloakTokenError,
    KeycloakTokenTemporaryError,
    NatsConnectionBuilder,
    ServiceClientError,
    ServiceClientWrapper,
    ServiceClientWrapperError,
    ServiceFactoryRegistry,
    Settings,
    SqliteConfig,
    TokenValidationError,
    UnsupportedServiceError,
    build_service_log_event,
    check_all_services,
    load_settings,
    mask_sensitive_value,
    retry_call,
)
```

> 위 목록은 `docmesh_py_core/__init__.py`의 `__all__` 기준입니다.

## 1.1 권장 호출 순서

대부분의 소비 애플리케이션은 아래 순서로 SDK를 사용합니다.

1. 환경변수 준비
2. `load_settings(env)` 호출
3. `ServiceFactoryRegistry(settings)` 생성
4. 필요한 서비스만 `create_client()`로 획득
5. 시작 시점에 `check()` 또는 `check_all_services()` 실행
6. 종료 시 `close_all()` 호출

주의:

- `nats`만 예외적으로 `NatsConnectionBuilder`를 반환하며, 실제 연결은 `await connect()/ping()/check()`에서 일어납니다.
- `langfuse`는 `LANGFUSE_ENABLED=false`면 `None`이 될 수 있으므로 소비 코드에서 분기 처리가 필요합니다.

## 2. Settings API

### `load_settings(env) -> Settings`

환경변수 매핑에서 전체 설정을 읽고 검증합니다.

주요 동작:

- 서비스별 설정 객체 생성
- 필수값/타입/범위 검증
- 선택적 설정(`postgres`, `sqlite`)은 관련 env가 없으면 `None`
- 검증 실패 시 `ConfigError` 발생
- `LANGFUSE_ENVIRONMENT`가 비어 있으면 `DOCMESH_ENV` 값을 상속

입력:

- `env`: `Mapping[str, str]` 형태의 환경변수 집합

대표 예외:

- `ConfigError`: 필수값 누락, bool/정수 파싱 실패, 범위 위반, 상호배타 검증 실패

예시:

```python
from os import environ
from docmesh_py_core import load_settings

settings = load_settings(environ)
print(settings.common.env)
```

### `Settings`

패키지의 최상위 설정 객체입니다.

하위 설정 필드:

- `settings.common`
- `settings.keycloak`
- `settings.postgres` (`None` 가능)
- `settings.sqlite` (`None` 가능)
- `settings.minio`
- `settings.milvus`
- `settings.ollama`
- `settings.langfuse`
- `settings.nats`

환경변수 계약은 [config.md](./config.md)를 참고하세요.

### `SqliteConfig`

SQLite 전용 설정 객체입니다.

대표 항목:

- `path`
- `readonly`
- `enable_wal`
- `busy_timeout_ms`

## 3. Client factory API

### `ServiceFactoryRegistry(settings)`

외부 서비스 클라이언트를 생성하는 진입점입니다.

주요 메서드:

- `create_client(service_name)`
- `create_clients(services)`
- `close_all()`

지원 서비스명:

- `keycloak`
- `postgres`
- `sqlite`
- `minio`
- `milvus`
- `ollama`
- `langfuse`
- `nats`

개발 시 알아둘 점:

- `create_client()`는 동일 서비스에 대해 이미 생성한 클라이언트를 재사용합니다.
- `postgres`와 `sqlite`는 내부적으로 SQLAlchemy Engine 기반 객체를 래핑합니다.
- `langfuse`는 설정상 비활성화되면 `None`이 반환될 수 있습니다.
- `nats`는 다른 서비스와 달리 sync wrapper가 아니라 async builder입니다.

예시:

```python
registry = ServiceFactoryRegistry(settings)
postgres = registry.create_client("postgres")
postgres.check()
registry.close_all()
```

### `create_client(service_name) -> ServiceClientWrapper | NatsConnectionBuilder | None`

단일 서비스 클라이언트를 생성하거나 재사용합니다.

입력:

- `service_name`: `keycloak`, `postgres`, `sqlite`, `minio`, `milvus`, `ollama`, `langfuse`, `nats`

반환:

- 대부분 서비스: `ServiceClientWrapper`
- `nats`: `NatsConnectionBuilder`
- `langfuse`: 비활성화 시 `None`

대표 예외:

- `UnsupportedServiceError`: 지원하지 않는 서비스명

### `create_clients(services) -> dict[str, Any]`

여러 서비스 클라이언트를 한 번에 생성합니다.

입력:

- `services`: 서비스명 iterable

반환:

- 서비스명 → 클라이언트/빌더 매핑

### `close_all() -> None`

지금까지 생성한 모든 클라이언트의 종료 훅을 호출합니다.

주의:

- `ServiceClientWrapper`는 `close_fn`이 있으면 그 함수를 우선 사용합니다.
- NATS builder 자체는 장기 연결을 보관하지 않으므로 `check()` 내부에서 연결 후 정리됩니다.

반환 타입 요약:

| 서비스 | 반환값 |
| --- | --- |
| `keycloak` | `ServiceClientWrapper` |
| `postgres` | `ServiceClientWrapper` |
| `sqlite` | `ServiceClientWrapper` |
| `minio` | `ServiceClientWrapper` |
| `milvus` | `ServiceClientWrapper` |
| `ollama` | `ServiceClientWrapper` |
| `langfuse` | `ServiceClientWrapper \| None` |
| `nats` | `NatsConnectionBuilder` |

대표 예외:

- `UnsupportedServiceError`
- `ServiceClientWrapperError`
- `ServiceClientError`

### `ServiceClientWrapper`

공통 `ping()` / `check()` / `close()` 인터페이스를 제공하는 래퍼입니다.

핵심 메서드:

- `ping()` — 내부 healthcheck 호출, 실패 시 `ServiceClientWrapperError`로 변환
- `check()` — `ping()`의 별칭
- `close()` — 서비스별 close/dispose/flush 호출

실무 팁:

- SQLAlchemy 기반 서비스(`postgres`, `sqlite`)는 wrapper를 통해 `connect()`를 그대로 사용할 수 있습니다.
- healthcheck 실패 예외는 서비스명/operation/error_type 정보를 포함한 래퍼 오류로 표준화됩니다.

일반적인 사용 예:

```python
client = registry.create_client("sqlite")
client.check()
client.close()
```

기본 `check()` 동작:

| 서비스 | 기본 확인 |
| --- | --- |
| Keycloak | `fetch_access_token()` |
| PostgreSQL | `SELECT 1` |
| SQLite | `SELECT 1` |
| MinIO | `list_buckets()` |
| Milvus | `list_collections()` |
| Ollama | `ps()` |
| Langfuse | `auth_check()` |

### `NatsConnectionBuilder`

NATS 연결용 비동기 builder입니다.

- `create_client("nats")`의 반환값
- 실제 연결은 `await connect()`, `await ping()`, `await check()`로 수행
- `connect_kwargs` 프로퍼티로 최종 연결 인자를 확인 가능

개발 시 알아둘 점:

- 장기 연결을 보관하는 커넥션 풀 객체가 아니라 "연결 시도용 builder"입니다.
- `check()`는 연결 후 `flush()`를 호출하고 바로 연결을 정리합니다.
- 애플리케이션이 실제 지속 연결을 원하면 `await connect()` 결과를 직접 관리해야 합니다.

예시:

```python
import asyncio

builder = registry.create_client("nats")
asyncio.run(builder.check())
```

## 4. Health API

### `check_all_services(service_checks, required_services=None, parallel=False)`

여러 서비스의 헬스체크를 집계 실행합니다.

입력:

- `service_checks`: 서비스명 → 인자 없는 callable 매핑
- `required_services`: 실패 시 즉시 예외를 발생시킬 서비스 집합
- `parallel`: `True`면 thread pool 기반 병렬 실행

반환:

- `HealthCheckResult.ok`
- `HealthCheckResult.services`

개발 시 알아둘 점:

- `parallel=False`에서는 순차 실행 중 required 서비스 실패 시 즉시 `HealthCheckError`를 발생시킵니다.
- `parallel=True`에서는 전체 결과를 수집한 뒤 required 서비스 실패 여부를 판단합니다.
- 오류 문자열은 `mask_sensitive_value()`를 거쳐 민감정보를 숨깁니다.

예시:

```python
result = check_all_services(
    {
        "postgres": postgres.check,
        "minio": minio.check,
    },
    required_services={"postgres"},
    parallel=True,
)
```

대표 예외:

- `HealthCheckError`: 필수 서비스 실패 시

## 5. Keycloak API

### `KeycloakAuthService(settings, *, http_client=None, verification_key=None, allowed_algorithms=None, logger=None, event_logger=None, timer=time.perf_counter, sleep=time.sleep, current_time=time.time)`

Keycloak 인증 관련 고수준 진입점입니다.

제공 기능:

- Access Token 획득
- JWT 검증
- 사용자 정보 및 역할 추출

참고:

- 기본 허용 알고리즘은 `['HS256']`입니다.
- RS256/JWKS 검증을 사용하려면 `allowed_algorithms`에 `RS256`을 포함해야 합니다.
- `verification_key`는 HS256 검증 시 필요합니다.

### `fetch_access_token(scope=None, username=None, password=None) -> AccessTokenResult`

Keycloak token endpoint에서 access token을 요청합니다.

기본 특성:

- 기본 grant: `client_credentials`
- 선택적 `scope` 전달 지원
- 명시적 설정 시 `password` grant 사용 가능
- `password` grant에서는 함수 인자 `username`, `password`를 사용
- `max_retries + 1` 회까지 재시도 시도

입력:

- `scope`: 선택적 OAuth scope override
- `username`: `password` grant에서 사용할 사용자명
- `password`: `password` grant에서 사용할 비밀번호

반환 필드:

- `access_token`
- `token_type`
- `expires_in`
- `refresh_token`
- `scope`

대표 예외:

- `KeycloakTokenConfigurationError`
- `KeycloakTokenAuthenticationError`
- `KeycloakTokenTemporaryError`
- `KeycloakTokenError`

개발 시 알아둘 점:

- HTTP `400/401/403`은 인증 오류로 분류됩니다.
- HTTP `408/429` 및 `5xx`는 일시적 오류로 분류되어 재시도 대상이 됩니다.
- 응답 JSON에 `access_token`, `token_type`, `expires_in`이 없으면 `KeycloakTokenError`가 발생합니다.
- `password` grant인데 `username` 또는 `password` 인자가 빠지면 `KeycloakTokenConfigurationError`가 발생합니다.

### `extract_user_info(token) -> AuthenticatedUser`

JWT를 검증한 뒤 표준 사용자 정보를 반환합니다.

입력:

- raw JWT 문자열
- `Bearer <token>` 형식 문자열

검증 항목:

- 서명
- 만료 시간
- issuer
- 선택적 audience
- 허용 알고리즘

추가 동작:

- subject는 `sub` 우선, 없으면 `jti`를 대체 식별자로 사용합니다.
- `realm_access.roles`와 `resource_access.*.roles`를 각각 `realm_roles`, `client_roles`로 분리합니다.

반환 필드:

- `sub`
- `preferred_username`
- `email`
- `given_name`
- `family_name`
- `name`
- `realm_roles`
- `client_roles`
- `claims`

대표 예외:

- `TokenValidationError`

개발 시 알아둘 점:

- 기본 설정만 사용하면 HS256 검증만 허용됩니다.
- Keycloak의 일반적인 RS256 토큰을 검증하려면 `allowed_algorithms=['RS256']` 구성이 필요합니다.
- RS256 검증 시 JWKS는 `KEYCLOAK_JWKS_CACHE_TTL_SECONDS` 기준으로 캐시됩니다.

### `AccessTokenResult`

토큰 응답 객체입니다.

대표 필드:

- `access_token`
- `token_type`
- `expires_in`
- `refresh_token`
- `scope`

### `AuthenticatedUser`

검증된 토큰에서 추출한 사용자 정보 객체입니다.

대표 필드:

- `sub`
- `preferred_username`
- `email`
- `given_name`
- `family_name`
- `name`
- `realm_roles`
- `client_roles`
- `claims`

### `KeycloakProvisioner(settings, *, admin_client)`

Keycloak Realm/Client/Role을 선언형으로 생성/갱신하는 프로비저너입니다.

주요 특징:

- 멱등 실행
- Dry-run 지원
- 생성/갱신/변경 없음/실패 구분
- 선언에서 제거된 리소스 자동 삭제 없음

`admin_client`는 다음 계약을 만족해야 합니다.

- `ensure_realm(config)`
- `ensure_client(config)`
- `ensure_realm_role(realm, role_name)`
- `ensure_client_role(realm, client_id, role_name)`

### `provision() -> ProvisioningResult`

프로비저닝 결과는 다음 필드를 가집니다.

- `created`
- `updated`
- `unchanged`
- `failed`
- `planned`
- `dry_run`

실무 팁:

- dry-run이면 `planned`만 채워지고 실제 생성/갱신은 수행하지 않습니다.
- 각 operation 실패는 전체 중단 대신 `failed`에 누적됩니다.
- admin client는 호출 결과로 `created` / `updated` / 그 외(unchanged)를 반환해야 문서된 집계가 성립합니다.

## 6. Utility API

### `mask_sensitive_value(raw)`

비밀번호, 토큰, secret, DSN/URI의 민감값을 마스킹합니다.

### `build_service_log_event(...)`

서비스 연결/헬스체크/재시도 이벤트를 구조화된 `dict`로 생성합니다.

표준 키:

- `service`
- `operation`
- `outcome`
- `host`
- `latency_ms`
- `retry_count`
- `error`

### `retry_call(operation, ..., retry_on, max_attempts, base_delay_seconds=0.5)`

일시적 오류에 대해 동기 함수를 재시도합니다.

주의:

- `max_attempts < 1` 이면 `ValueError`를 발생시킵니다.
- 재시도 간격은 `base_delay_seconds * 2 ** (attempt - 1)` 지수 백오프입니다.

## 7. Public API usage notes

- 일반 소비 코드는 패키지 루트 import를 권장합니다.
- 서비스별 환경변수 활성화 규칙은 [config.md](./config.md)에서 확인하세요.
- 실제 앱 코드 조합 예시는 [examples.md](./examples.md)를 참고하세요.
- 워크플로우 중심 사용법은 [README](../README.md)를 먼저 읽는 것이 좋습니다.
