# docmesh-py-core API 가이드

이 문서는 `docmesh-py-core`를 다른 애플리케이션에서 사용할 때 필요한 공개 API만 간결하게 정리한 문서다.

이 문서의 범위:

- 무엇을 import 하는가
- 어떤 순서로 사용하는가
- 각 공개 API의 역할, 반환값, 대표 예시

세부 환경변수 규칙, 기본값, 조건부 필수값은 [설정 가이드](./config.md)를 참고한다.
통합/단위 테스트 전략은 [테스트 가이드](./test.md)를 참고한다.

---

## 1. 빠른 시작

가장 일반적인 사용 흐름은 아래와 같다.

1. 환경변수로 설정을 준비한다.
2. `load_settings()`로 설정을 검증한다.
3. `ServiceFactoryRegistry`로 서비스 client를 만든다.
4. `check()` 또는 실제 SDK 메서드를 호출한다.

```python
from docmesh_py_core import ServiceFactoryRegistry, load_settings

settings = load_settings(env)
registry = ServiceFactoryRegistry(settings)

postgres = registry.create_client("postgres")
postgres.check()

with postgres.connect() as conn:
    conn.exec_driver_sql("SELECT 1")

registry.close_all()
```

---

## 2. 공개 API

패키지 루트에서 바로 import 가능한 API:

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
    ServiceClientWrapper,
    ServiceFactoryRegistry,
    Settings,
    TokenValidationError,
    check_all_services,
    load_settings,
    mask_sensitive_value,
)
```

권장:

- 일반 사용자는 `docmesh_py_core` 루트에서 import 한다.
- 하위 모듈 직접 import는 특별한 이유가 있을 때만 사용한다.

---

## 3. 설정 API

### `load_settings(env) -> Settings`

역할:

- 환경변수 매핑에서 전체 설정을 읽는다.
- 서비스별 설정을 검증한다.
- 검증 실패 시 `ConfigError`를 발생시킨다.

예시:

```python
from os import environ
from docmesh_py_core import load_settings

settings = load_settings(environ)
print(settings.common.env)
print(settings.keycloak.url)
```

대표 예외:

- `ConfigError`: 필수값 누락, 형식 오류, 상호배타 규칙 위반, 운영 보안 규칙 위반

### `Settings`

역할:

- 패키지의 최상위 설정 객체다.
- 아래 서비스 설정을 묶어 제공한다.

주요 필드:

- `settings.common`
- `settings.keycloak`
- `settings.postgres`
- `settings.minio`
- `settings.milvus`
- `settings.ollama`
- `settings.langfuse`
- `settings.nats`

참고:

- 환경변수 이름, 기본값, 조건부 필수 규칙은 `./config.md`를 참고한다.

---

## 4. 서비스 클라이언트 API

### `ServiceFactoryRegistry`

정의:

```python
registry = ServiceFactoryRegistry(settings)
```

주요 메서드:

- `create_client(service_name)`
- `create_clients(services)`
- `close_all()`

지원 서비스명:

- `keycloak`
- `postgres`
- `minio`
- `milvus`
- `ollama`
- `langfuse`
- `nats`

예시:

```python
registry = ServiceFactoryRegistry(settings)
postgres = registry.create_client("postgres")
minio = registry.create_client("minio")
postgres.check()
minio.check()
```

반환 규칙:

| 서비스 | 반환값 |
| --- | --- |
| `keycloak` | `ServiceClientWrapper` |
| `postgres` | `ServiceClientWrapper` |
| `minio` | `ServiceClientWrapper` |
| `milvus` | `ServiceClientWrapper` |
| `ollama` | `ServiceClientWrapper` |
| `langfuse` | `ServiceClientWrapper \| None` |
| `nats` | `NatsConnectionBuilder` |

주의:

- `langfuse`는 비활성화 시 `None`일 수 있다.
- `nats`는 연결된 client가 아니라 비동기 builder다.
- 지원하지 않는 서비스명은 `KeyError`가 발생한다.

### `ServiceClientWrapper`

역할:

- 서비스별 SDK 위에 공통 `ping()` / `check()` / `close()` 인터페이스를 제공한다.
- 원본 client 메서드는 그대로 위임한다.

예시:

```python
postgres = registry.create_client("postgres")
postgres.check()
postgres.connect()
postgres.close()
```

기본 `check()` 동작:

| 서비스 | 동작 |
| --- | --- |
| Keycloak | `fetch_access_token()` |
| PostgreSQL | `SELECT 1` |
| MinIO | `list_buckets()` |
| Milvus | `list_collections()` |
| Ollama | `ps()` |
| Langfuse | `auth_check()` |

---

## 5. NATS API

### `NatsConnectionBuilder`

역할:

- NATS 연결 인자를 보관한다.
- `connect()` 호출 시 실제 연결을 만든다.
- `check()`는 연결 후 `flush()`까지 수행한다.

예시:

```python
import asyncio

builder = registry.create_client("nats")

async def main() -> None:
    await builder.check()

asyncio.run(main())
```

주의:

- `create_client("nats")` 결과는 동기 client가 아니다.
- 반드시 `await builder.connect()` 또는 `await builder.check()`로 사용한다.

---

## 6. 헬스체크 API

### `check_all_services(service_checks, required_services=None)`

역할:

- 여러 서비스의 health check 함수를 한 번에 실행한다.
- 서비스별 성공 여부, 지연 시간, 오류를 집계한다.
- 필수 서비스가 실패하면 `HealthCheckError`를 발생시킨다.

예시:

```python
from docmesh_py_core import check_all_services

result = check_all_services(
    {
        "postgres": postgres.check,
        "minio": minio.check,
    },
    required_services={"postgres"},
)

print(result.ok)
for item in result.services:
    print(item.service, item.ok, item.latency_ms, item.error)
```

관련 타입:

- `HealthCheckResult.ok`: 전체 성공 여부
- `HealthCheckResult.services`: 서비스별 상태 목록
- `HealthCheckError.service`: 실패한 필수 서비스명
- `HealthCheckError.error`: 마스킹된 오류 메시지

---

## 7. Keycloak API

### `KeycloakAuthService`

역할:

- Keycloak access token 발급
- JWT 검증 및 사용자 정보 추출

생성 예시:

```python
from docmesh_py_core import KeycloakAuthService

auth = KeycloakAuthService(settings, allowed_algorithms=["RS256"])
```

### `fetch_access_token(scope=None) -> AccessTokenResult`

역할:

- Keycloak token endpoint에서 access token을 요청한다.
- `client_credentials`, `password` grant를 지원한다.

예시:

```python
token = auth.fetch_access_token()
print(token.access_token)
print(token.token_type)
print(token.expires_in)
```

반환값:

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

역할:

- JWT를 검증한 뒤 사용자 정보와 role을 추출한다.
- `Bearer <token>` 형식도 허용한다.

검증 항목:

- 알고리즘
- 서명
- issuer
- expiry
- audience(설정된 경우)

예시:

```python
user = auth.extract_user_info(raw_jwt)
print(user.sub)
print(user.preferred_username)
print(user.realm_roles)
print(user.client_roles)
```

반환값:

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

### `KeycloakProvisioner`

역할:

- realm, client, role 상태를 원하는 선언에 맞춘다.
- 실제 Admin API 호출은 외부 `admin_client` 구현에 위임한다.

기대 계약:

```python
class KeycloakAdminClient(Protocol):
    def ensure_realm(self, config) -> str: ...
    def ensure_client(self, config) -> str: ...
    def ensure_realm_role(self, realm: str, role_name: str) -> str: ...
    def ensure_client_role(self, realm: str, client_id: str, role_name: str) -> str: ...
```

예시:

```python
provisioner = KeycloakProvisioner(settings, admin_client=my_admin_client)
result = provisioner.provision()
print(result.created, result.updated, result.failed)
```

반환값:

- `created`
- `updated`
- `unchanged`
- `failed`
- `planned`
- `dry_run`

---

## 8. 보안 유틸리티

### `mask_sensitive_value(raw)`

역할:

- DSN, URL, query string, 일반 문자열에서 민감정보를 마스킹한다.
- password, secret, token, api_key 계열 문자열을 숨긴다.

예시:

```python
from docmesh_py_core import mask_sensitive_value

print(mask_sensitive_value("password=hunter2"))
print(mask_sensitive_value("token: abc123"))
```

사용 시점:

- 로그 출력 전
- 예외 메시지 노출 전
- 운영 화면에 연결 정보나 오류를 보여주기 전

---

## 9. 자주 하는 실수

### `Settings()`를 바로 생성하는 것

가능하지만 보통은 `load_settings()`를 권장한다.
이유는 검증과 오류 메시지 정리가 함께 이뤄지기 때문이다.

### `create_client("nats")` 결과를 바로 동기 client처럼 쓰는 것

반환값은 연결된 client가 아니라 `NatsConnectionBuilder`다.
반드시 `await builder.connect()` 또는 `await builder.check()`를 사용해야 한다.

### `langfuse`가 항상 client를 반환한다고 가정하는 것

`LANGFUSE_ENABLED=false`면 `create_client("langfuse")`는 `None`일 수 있다.

---

## 10. 빠른 참조

설정 로드:

```python
settings = load_settings(env)
```

registry 생성:

```python
registry = ServiceFactoryRegistry(settings)
```

서비스 client 생성:

```python
postgres = registry.create_client("postgres")
```

공통 health check:

```python
postgres.check()
```

서비스 집계 health check:

```python
result = check_all_services({"postgres": postgres.check})
```

Keycloak token 발급:

```python
token = KeycloakAuthService(settings).fetch_access_token()
```

JWT 검증:

```python
user = KeycloakAuthService(settings, allowed_algorithms=["RS256"]).extract_user_info(jwt)
```

민감정보 마스킹:

```python
safe = mask_sensitive_value(raw_message)
```

---

## 11. 관련 문서

- [설정 가이드](./config.md)
- [테스트 가이드](./test.md)
