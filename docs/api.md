# docmesh-py-core API Reference

이 문서는 `docmesh-py-core`의 **공개 API 레퍼런스**입니다.

- 사용 흐름을 먼저 알고 싶다면 [README](../README.md)와 [SDK 가이드](./sdk.md)를 읽으세요.
- 환경변수와 설정 규칙은 [설정 가이드](./config.md)를 참고하세요.

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
    Page,
    ServiceClientError,
    ServiceClientWrapper,
    ServiceClientWrapperError,
    ServiceFactoryRegistry,
    Settings,
    SqliteConfig,
    TokenValidationError,
    UnsupportedServiceError,
    build_service_log_event,
    build_settings_snapshot,
    check_all_services,
    load_settings,
    mask_sensitive_value,
    retry_call,
    to_serializable,
)
```

## 2. Settings API

### `load_settings(env) -> Settings`

환경변수 매핑에서 전체 설정을 읽고 검증합니다.

주요 동작:

- 서비스별 설정 객체 생성
- 필수값/타입/범위 검증
- 검증 실패 시 `ConfigError` 발생

예시:

```python
from os import environ
from docmesh_py_core import load_settings

settings = load_settings(environ)
print(settings.common.env)
```

### `Settings`

패키지의 최상위 설정 객체입니다.

주요 하위 설정:

- `settings.common`
- `settings.keycloak`
- `settings.postgres`
- `settings.sqlite`
- `settings.minio`
- `settings.milvus`
- `settings.ollama`
- `settings.langfuse`
- `settings.nats`

환경변수 계약은 [config.md](./config.md)를 참고하세요.

### `SqliteConfig`

SQLite 전용 설정 객체입니다.

대표 항목:

- 파일 경로 또는 `:memory:`
- 읽기 전용 여부
- WAL 활성화 여부
- busy timeout

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

예시:

```python
registry = ServiceFactoryRegistry(settings)
postgres = registry.create_client("postgres")
postgres.check()
registry.close_all()
```

반환 타입:

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

공통 `check()` / `close()` 인터페이스를 제공하는 래퍼입니다.

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
- 실제 연결은 `await connect()` 또는 `await check()`로 수행

예시:

```python
import asyncio

builder = registry.create_client("nats")
asyncio.run(builder.check())
```

## 4. Health API

### `check_all_services(service_checks, required_services=None, parallel=False)`

여러 서비스의 헬스체크를 집계 실행합니다.

반환 정보:

- 전체 성공 여부
- 서비스별 성공 여부
- 서비스별 지연 시간
- 마스킹된 오류 메시지

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

### `KeycloakAuthService(settings, allowed_algorithms=None)`

Keycloak 인증 관련 고수준 진입점입니다.

제공 기능:

- Access Token 획득
- JWT 검증
- 사용자 정보 및 역할 추출

### `fetch_access_token(scope=None) -> AccessTokenResult`

Keycloak token endpoint에서 access token을 요청합니다.

기본 특성:

- 기본 grant: `client_credentials`
- 선택적 `scope` 전달 지원
- 명시적 설정 시 `password` grant 사용 가능

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
- `name`
- `realm_roles`
- `client_roles`
- `claims`

### `KeycloakProvisioner`

Keycloak Realm/Client/Role을 선언형으로 생성/갱신하는 프로비저너입니다.

주요 특징:

- 멱등 실행
- Dry-run 지원
- 생성/갱신/변경 없음/실패 구분
- 선언에서 제거된 리소스 자동 삭제 없음

## 6. Utility API

### `mask_sensitive_value(raw)`

비밀번호, 토큰, secret, DSN/URI의 민감값을 마스킹합니다.

### `build_service_log_event(...)`

서비스 연결/헬스체크/재시도 이벤트를 구조화된 dict로 생성합니다.

### `retry_call(operation, ..., retry_on, max_attempts)`

일시적 오류에 대해 동기 함수를 재시도합니다.

### `to_serializable(value)`

dataclass, Pydantic model, datetime 등 복합 값을 JSON 친화 구조로 변환합니다.

### `build_settings_snapshot(settings)`

민감정보가 마스킹된 설정 스냅샷을 생성합니다.

### `Page`

페이지네이션 표현용 공통 타입입니다.

## 7. Public API usage notes

- 일반 소비 코드는 패키지 루트 import를 권장합니다.
- 서비스별 환경변수 활성화 규칙은 [config.md](./config.md)에서 확인하세요.
- 워크플로우 중심 사용법은 [README](../README.md)와 [sdk.md](./sdk.md)를 먼저 읽는 것이 좋습니다.
