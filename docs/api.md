# docmesh-py-core API 가이드

이 문서는 `docmesh-py-core` 패키지를 다른 애플리케이션이나 서비스에서 바로 사용할 수 있도록,
공개 API의 목적, 입력, 출력, 예외, 사용 예시를 정리한 문서다.

목표는 다음과 같다.

- 이 문서만 보고 패키지 사용을 시작할 수 있어야 한다.
- 어떤 객체를 어디서 import 해야 하는지 바로 이해할 수 있어야 한다.
- 설정 로딩, 서비스 클라이언트 생성, 헬스체크, Keycloak 인증/토큰/JWT 검증 흐름을 예시로 따라갈 수 있어야 한다.

---

## 1. 패키지 개요

`docmesh-py-core`는 외부 서비스 연결을 위한 공통 코어 패키지다.

주요 역할:

- 환경변수 기반 설정 로딩과 검증
- 서비스별 SDK 클라이언트 생성
- 공통 `ping()` / `check()` 헬스체크 인터페이스 제공
- Keycloak access token 발급
- JWT 사용자 정보 추출 및 검증
- 민감정보 마스킹
- 여러 서비스의 헬스체크 결과 집계

지원 서비스:

- Keycloak
- PostgreSQL
- MinIO
- Milvus
- Ollama
- Langfuse
- NATS

중요 전제:

- 이 패키지는 런타임에서 필요한 SDK 의존성이 이미 설치되어 있다고 가정한다.
- 설정은 코드 하드코딩이 아니라 환경변수로 주입하는 방식이 기본이다.

---

## 2. 공개 API 목록

패키지 루트에서 바로 import 가능한 공개 API는 다음과 같다.

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

권장 import 원칙:

- 일반 사용자는 가능하면 `docmesh_py_core` 루트에서 import 한다.
- 구현 세부 타입이 꼭 필요할 때만 `docmesh_py_core.config`, `docmesh_py_core.health` 같은 하위 모듈을 직접 import 한다.

---

## 3. 가장 먼저 알아야 할 사용 흐름

대부분의 사용 흐름은 아래 4단계다.

1. 환경변수로 설정을 준비한다.
2. `load_settings()`로 설정 객체를 만든다.
3. `ServiceFactoryRegistry`로 서비스 클라이언트를 만든다.
4. `ping()` / `check()` 또는 실제 SDK 메서드를 호출한다.

최소 예시:

```python
from docmesh_py_core import ServiceFactoryRegistry, load_settings

settings = load_settings({
    "KEYCLOAK_URL": "https://keycloak.example.com",
    "KEYCLOAK_REALM": "docmesh",
    "KEYCLOAK_CLIENT_ID": "docmesh-backend",
    "KEYCLOAK_CLIENT_SECRET": "secret",
    "POSTGRES_HOST": "postgres.example.com",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "docmesh",
    "POSTGRES_USER": "docmesh",
    "POSTGRES_PASSWORD": "secret",
    "MINIO_ENDPOINT": "minio.example.com:9000",
    "MINIO_ACCESS_KEY": "access-key",
    "MINIO_SECRET_KEY": "secret-key",
    "MILVUS_URI": "http://milvus.example.com:19530",
    "OLLAMA_HOST": "http://ollama.example.com:11434",
    "LANGFUSE_ENABLED": "false",
    "NATS_SERVERS": "nats://n1.example.com:4222",
})

registry = ServiceFactoryRegistry(settings)
postgres = registry.create_client("postgres")

# 공통 health API
postgres.check()

# 원본 SDK 메서드도 그대로 사용 가능
with postgres.connect() as conn:
    conn.exec_driver_sql("SELECT 1")

registry.close_all()
```

---

## 4. 설정 API

### 4.1 `load_settings(env)`

정의:

```python
load_settings(env: Mapping[str, str]) -> Settings
```

기능:

- 전달받은 환경변수 매핑에서 설정을 읽는다.
- 서비스별 설정 모델을 검증한다.
- 검증 실패 시 `ConfigError`를 발생시킨다.
- `LANGFUSE_ENVIRONMENT`가 없으면 `DOCMESH_ENV` 값으로 자동 채운다.
- 운영 환경(`DOCMESH_ENV=production|prod`)에서는 일부 비보안 설정을 거부한다.

언제 쓰나:

- 테스트에서 명시적으로 설정을 주입할 때
- 애플리케이션이 자체적으로 환경변수/secret manager를 읽은 뒤 dict 형태로 전달할 때
- 프로세스 전체 환경 대신 부분 환경으로 설정을 생성하고 싶을 때

예시:

```python
from os import environ
from docmesh_py_core import load_settings

settings = load_settings(environ)
print(settings.common.env)
print(settings.keycloak.url)
print(settings.postgres.host)
```

예외:

- `ConfigError`
  - 필수 환경변수 누락
  - bool/int/range 검증 실패
  - 상호배타 인증 방식 충돌
  - 운영 환경 보안 규칙 위반

대표 실패 예시:

```python
from docmesh_py_core import ConfigError, load_settings

try:
    load_settings({
        "KEYCLOAK_URL": "https://keycloak.example.com",
        "KEYCLOAK_REALM": "docmesh",
        "KEYCLOAK_CLIENT_ID": "backend",
        # KEYCLOAK_CLIENT_SECRET 누락
        "POSTGRES_HOST": "postgres",
        "POSTGRES_DB": "docmesh",
        "POSTGRES_USER": "docmesh",
        "POSTGRES_PASSWORD": "secret",
        "MINIO_ENDPOINT": "minio:9000",
        "MINIO_ACCESS_KEY": "access",
        "MINIO_SECRET_KEY": "secret",
        "MILVUS_URI": "http://milvus:19530",
        "OLLAMA_HOST": "http://ollama:11434",
        "LANGFUSE_ENABLED": "false",
        "NATS_SERVERS": "nats://nats:4222",
    })
except ConfigError as exc:
    print(str(exc))
```

### 4.2 `Settings`

정의:

```python
class Settings(BaseSettings):
    common: CommonConfig
    keycloak: KeycloakConfig
    postgres: PostgresConfig
    minio: MinioConfig
    milvus: MilvusConfig
    ollama: OllamaConfig
    langfuse: LangfuseConfig
    nats: NatsConfig
```

기능:

- 전체 애플리케이션 설정의 최상위 객체다.
- 각 서비스 설정을 필드로 가진다.
- `load_settings()`가 일반적인 진입점이며, 반환값도 이 타입이다.

자주 쓰는 필드 예시:

```python
settings.common.env
settings.keycloak.url
settings.keycloak.client_id
settings.postgres.dsn
settings.postgres.host
settings.minio.endpoint
settings.milvus.uri
settings.ollama.host
settings.langfuse.enabled
settings.nats.servers
```

실무 팁:

- 패키지 외부 코드에서는 세부 검증 규칙을 직접 재구현하지 말고 `load_settings()`를 단일 진입점으로 사용한다.
- `Settings()`를 직접 생성하는 대신 `load_settings()`를 권장한다. 검증 실패 메시지가 더 사용자 친화적으로 정리되기 때문이다.

---

## 5. 서비스 클라이언트 팩토리 API

### 5.1 `ServiceFactoryRegistry`

정의:

```python
class ServiceFactoryRegistry:
    def create_client(self, service_name: str) -> Any: ...
    def create_clients(self, services: Iterable[str]) -> dict[str, Any]: ...
    def close_all(self) -> None: ...
```

기능:

- `Settings`를 기반으로 서비스 클라이언트를 lazy 생성한다.
- 대부분의 서비스는 `ServiceClientWrapper`로 감싸서 반환한다.
- NATS는 비동기 연결 특성 때문에 `NatsConnectionBuilder`를 반환한다.
- 이미 생성한 클라이언트는 내부 캐시에 재사용한다.

지원 `service_name` 값:

- `"keycloak"`
- `"postgres"`
- `"minio"`
- `"milvus"`
- `"ollama"`
- `"langfuse"`
- `"nats"`

기본 사용 예시:

```python
from docmesh_py_core import ServiceFactoryRegistry, load_settings

settings = load_settings(env)
registry = ServiceFactoryRegistry(settings)

keycloak = registry.create_client("keycloak")
postgres = registry.create_client("postgres")
minio = registry.create_client("minio")
```

여러 개 생성 예시:

```python
clients = registry.create_clients(["postgres", "minio", "ollama"])
clients["postgres"].check()
clients["minio"].check()
clients["ollama"].check()
```

정리 예시:

```python
registry.close_all()
```

예외:

- `KeyError`: 지원하지 않는 서비스명을 전달한 경우

### 5.2 반환 타입 규칙

`create_client()`의 반환 타입은 서비스별로 다르다.

| 서비스 | 반환 타입 | 설명 |
| --- | --- | --- |
| `keycloak` | `ServiceClientWrapper` | 내부 client는 `KeycloakAuthService` |
| `postgres` | `ServiceClientWrapper` | 내부 client는 SQLAlchemy engine |
| `minio` | `ServiceClientWrapper` | 내부 client는 `Minio` |
| `milvus` | `ServiceClientWrapper` | 내부 client는 `MilvusClient` |
| `ollama` | `ServiceClientWrapper` | 내부 client는 `ollama.Client` |
| `langfuse` | `ServiceClientWrapper \| None` | `LANGFUSE_ENABLED=false`면 `None` |
| `nats` | `NatsConnectionBuilder` | 비동기 연결 builder |

중요한 차이:

- `langfuse`는 비활성화되면 `None`일 수 있다.
- `nats`는 즉시 연결된 클라이언트가 아니라 "연결을 만드는 객체"다.

---

## 6. 공통 서비스 래퍼 API

### 6.1 `ServiceClientWrapper`

정의:

```python
@dataclass
class ServiceClientWrapper:
    client: Any
    healthcheck: Callable[[], Any]
    close_fn: Callable[[], Any] | None = None

    def ping(self) -> Any: ...
    def check(self) -> Any: ...
    def close(self) -> Any: ...
```

기능:

- 서비스별로 서로 다른 SDK 위에 공통 `ping()` / `check()` 인터페이스를 제공한다.
- 원본 client의 속성과 메서드는 `__getattr__()`로 그대로 위임한다.
- 따라서 `wrapper.check()`도 가능하고, `wrapper.some_sdk_method()`도 가능하다.

예시:

```python
postgres = registry.create_client("postgres")
postgres.check()          # 공통 health API
postgres.connect()        # SQLAlchemy engine 메서드 위임
postgres.close()          # dispose 호출
```

서비스별 기본 health 동작:

| 서비스 | `check()` 동작 |
| --- | --- |
| Keycloak | `fetch_access_token()` |
| PostgreSQL | `SELECT 1` 실행 |
| MinIO | `list_buckets()` |
| Milvus | `list_collections()` |
| Ollama | `ps()` |
| Langfuse | `auth_check()` |

주의:

- `check()`의 반환 타입은 서비스별 SDK 반환값을 그대로 따른다.
- 반환 타입을 통일해주지는 않으므로, 공통 처리보다 "성공/실패" 판정 용도로 쓰는 것이 좋다.

---

## 7. NATS 비동기 API

### 7.1 `NatsConnectionBuilder`

정의:

```python
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

    @property
    def connect_kwargs(self) -> dict[str, Any]: ...
    async def connect(self) -> Any: ...
    async def ping(self) -> Any: ...
    async def check(self) -> Any: ...
```

기능:

- NATS 연결 인자를 들고 있는 비동기 builder다.
- `connect()` 호출 시 실제 NATS 연결을 만든다.
- `ping()` / `check()`는 연결 후 `flush()`를 수행하고 종료 정리까지 포함한다.

예시:

```python
import asyncio
from docmesh_py_core import ServiceFactoryRegistry, load_settings

settings = load_settings(env)
registry = ServiceFactoryRegistry(settings)
builder = registry.create_client("nats")

async def main() -> None:
    await builder.check()

asyncio.run(main())
```

실제 publish/subscribe 예시:

```python
import asyncio

builder = registry.create_client("nats")

async def main() -> None:
    client = await builder.connect()
    try:
        await client.publish("events.demo", b"hello")
        await client.flush()
    finally:
        close = getattr(client, "drain", None) or getattr(client, "close", None)
        if close is not None:
            result = close()
            if hasattr(result, "__await__"):
                await result

asyncio.run(main())
```

주의:

- `create_client("nats")` 결과에 대해 바로 동기 방식으로 메서드를 호출하면 안 된다.
- 반드시 `await builder.connect()` 또는 `await builder.check()` 방식으로 사용한다.

---

## 8. 헬스체크 집계 API

### 8.1 `check_all_services(service_checks, required_services=None, timer=time.perf_counter)`

정의:

```python
check_all_services(
    service_checks: Mapping[str, Callable[[], object]],
    *,
    required_services: set[str] | None = None,
    timer: Callable[[], float] = time.perf_counter,
) -> HealthCheckResult
```

기능:

- 여러 서비스의 health check 함수를 한 번에 실행한다.
- 서비스별 성공 여부와 지연 시간을 수집한다.
- 예외 메시지는 `mask_sensitive_value()`를 거쳐 민감정보를 숨긴다.
- 필수 서비스가 실패하면 `HealthCheckError`를 발생시킨다.

가장 흔한 사용 패턴:

```python
from docmesh_py_core import ServiceFactoryRegistry, check_all_services, load_settings

settings = load_settings(env)
registry = ServiceFactoryRegistry(settings)

postgres = registry.create_client("postgres")
minio = registry.create_client("minio")
ollama = registry.create_client("ollama")

result = check_all_services(
    {
        "postgres": postgres.check,
        "minio": minio.check,
        "ollama": ollama.check,
    },
    required_services={"postgres", "minio"},
)

print(result.ok)
for service in result.services:
    print(service.service, service.ok, service.latency_ms, service.error)
```

반환값 개요:

- `result.ok`: 전체 성공 여부
- `result.services`: 서비스별 상태 목록
  - `service`: 서비스명
  - `ok`: 성공 여부
  - `latency_ms`: 응답 시간(ms)
  - `error`: 실패 시 마스킹된 오류 메시지

예외:

- `HealthCheckError`
  - `service`: 실패한 필수 서비스명
  - `error`: 마스킹된 오류 메시지

필수 서비스 실패 예시:

```python
from docmesh_py_core import HealthCheckError, check_all_services

try:
    check_all_services(
        {
            "postgres": lambda: (_ for _ in ()).throw(RuntimeError("password=hunter2")),
        },
        required_services={"postgres"},
    )
except HealthCheckError as exc:
    print(exc.service)  # postgres
    print(exc.error)    # password=*** 형태로 마스킹됨
```

---

## 9. Keycloak 인증 API

### 9.1 `KeycloakAuthService`

정의:

```python
class KeycloakAuthService:
    def __init__(
        self,
        settings: Settings,
        *,
        http_client: KeycloakHttpClient | None = None,
        verification_key: str | None = None,
        allowed_algorithms: list[str] | None = None,
    ) -> None: ...

    def fetch_access_token(self, *, scope: str | None = None) -> AccessTokenResult: ...
    def extract_user_info(self, token: str) -> AuthenticatedUser: ...

    @property
    def issuer(self) -> str: ...

    @property
    def token_endpoint(self) -> str: ...

    @property
    def jwks_endpoint(self) -> str: ...
```

기능:

- Keycloak OIDC token endpoint에 access token 요청
- JWT 서명/issuer/audience/expiry 검증
- JWT에서 사용자 기본 정보와 role 추출

#### 9.1.1 `fetch_access_token()`

지원 grant:

- `client_credentials`
- `password`

기본 예시:

```python
from docmesh_py_core import KeycloakAuthService, load_settings

settings = load_settings(env)
auth = KeycloakAuthService(settings)
token = auth.fetch_access_token()

print(token.access_token)
print(token.token_type)
print(token.expires_in)
```

scope override 예시:

```python
token = auth.fetch_access_token(scope="openid profile email")
```

반환 타입: `AccessTokenResult`

필드:

- `access_token: str`
- `token_type: str`
- `expires_in: int`
- `refresh_token: str | None`
- `scope: str | None`

예외:

- `KeycloakTokenConfigurationError`
  - 설정 자체가 잘못된 경우
  - 예: password grant인데 username/password 누락
- `KeycloakTokenAuthenticationError`
  - 400/401/403 계열 인증 실패
- `KeycloakTokenTemporaryError`
  - 408/429/5xx 계열 일시적 실패
- `KeycloakTokenError`
  - 그 외 일반 토큰 요청 실패

실패 처리 예시:

```python
from docmesh_py_core import (
    KeycloakAuthService,
    KeycloakTokenAuthenticationError,
    KeycloakTokenTemporaryError,
)

try:
    token = KeycloakAuthService(settings).fetch_access_token()
except KeycloakTokenAuthenticationError:
    # client id / secret / user credential 확인
    raise
except KeycloakTokenTemporaryError:
    # 재시도 후보
    raise
```

#### 9.1.2 `extract_user_info(token)`

기능:

- JWT 문자열을 검증한 뒤 사용자 정보를 구조화된 객체로 반환한다.
- `Bearer ...` 접두어가 붙은 토큰도 허용한다.

검증 항목:

- 지원 알고리즘 여부 (`allowed_algorithms`)
- 서명 검증
- issuer 검증
- 만료(exp) 검증
- audience 검증 (`settings.keycloak.audience`가 설정된 경우)

예시:

```python
from docmesh_py_core import KeycloakAuthService

user = KeycloakAuthService(settings, allowed_algorithms=["RS256"]).extract_user_info(raw_jwt)

print(user.sub)
print(user.preferred_username)
print(user.realm_roles)
print(user.client_roles)
```

반환 타입: `AuthenticatedUser`

필드:

- `sub: str`
- `preferred_username: str | None`
- `email: str | None`
- `given_name: str | None`
- `family_name: str | None`
- `name: str | None`
- `realm_roles: list[str]`
- `client_roles: dict[str, list[str]]`
- `claims: dict[str, Any]`

예외:

- `TokenValidationError`
  - 형식 오류
  - 미지원 알고리즘
  - 서명 불일치
  - issuer 불일치
  - audience 불일치
  - 만료 토큰
  - JWKS 조회 실패

HS256 예시:

```python
auth = KeycloakAuthService(
    settings,
    verification_key="shared-secret",
    allowed_algorithms=["HS256"],
)
user = auth.extract_user_info(token)
```

RS256/JWKS 예시:

```python
auth = KeycloakAuthService(
    settings,
    allowed_algorithms=["RS256"],
)
user = auth.extract_user_info(token)
```

이 경우 JWKS는 아래 endpoint를 사용한다.

```python
auth.jwks_endpoint
```

---

## 10. Keycloak 프로비저닝 API

### 10.1 `KeycloakProvisioner`

정의:

```python
class KeycloakProvisioner:
    def __init__(self, settings: Settings, *, admin_client: KeycloakAdminClient) -> None: ...
    def provision(self) -> ProvisioningResult: ...
```

기능:

- Keycloak realm, client, role 상태를 원하는 선언과 맞춘다.
- 실제 Keycloak Admin API 호출은 외부 `admin_client`에 위임한다.
- dry-run 모드와 결과 집계를 제공한다.

이 패키지가 기대하는 `admin_client` 계약:

```python
class KeycloakAdminClient(Protocol):
    def ensure_realm(self, config) -> str: ...
    def ensure_client(self, config) -> str: ...
    def ensure_realm_role(self, realm: str, role_name: str) -> str: ...
    def ensure_client_role(self, realm: str, client_id: str, role_name: str) -> str: ...
```

각 메서드는 보통 다음 중 하나를 반환해야 한다.

- `"created"`
- `"updated"`
- `"unchanged"`

기본 예시:

```python
from docmesh_py_core import KeycloakProvisioner, load_settings

class MyAdminClient:
    def ensure_realm(self, config):
        return "created"

    def ensure_client(self, config):
        return "updated"

    def ensure_realm_role(self, realm, role_name):
        return "unchanged"

    def ensure_client_role(self, realm, client_id, role_name):
        return "created"

settings = load_settings(env)
provisioner = KeycloakProvisioner(settings, admin_client=MyAdminClient())
result = provisioner.provision()

print(result.created)
print(result.updated)
print(result.unchanged)
print(result.failed)
```

반환 타입: `ProvisioningResult`

필드:

- `created: list[str]`
- `updated: list[str]`
- `unchanged: list[str]`
- `failed: list[tuple[str, str]]`
- `planned: list[str]`
- `dry_run: bool`

dry-run 동작:

- `KEYCLOAK_PROVISIONING_DRY_RUN=true`이면 실제 `admin_client` 호출 없이 `planned`만 채운다.

실패 처리:

- 개별 항목 실패는 `failed`에 누적된다.
- 실패 메시지는 민감정보 마스킹 후 저장된다.
- 전체 작업이 일부 실패해도 즉시 예외를 던지지 않고 계속 진행한다.

---

## 11. 보안 유틸리티 API

### 11.1 `mask_sensitive_value(raw)`

정의:

```python
mask_sensitive_value(raw: str | None) -> str | None
```

기능:

- URL, DSN, query string, 일반 텍스트에서 민감정보를 마스킹한다.
- 키 이름에 `password`, `secret`, `token`, `api_key`, `client_secret` 등이 포함되면 마스킹 대상으로 본다.

예시:

```python
from docmesh_py_core import mask_sensitive_value

print(mask_sensitive_value("postgresql://user:secret@db.example.com:5432/app"))
print(mask_sensitive_value("password=hunter2"))
print(mask_sensitive_value("token: abc123"))
```

예상 결과 형태:

```python
"postgresql://user:***@db.example.com:5432/app"
"password=***"
"token: ***"
```

언제 쓰나:

- 예외 메시지를 로그로 남기기 전
- 외부 서비스 연결 문자열을 출력할 때
- 운영 이슈 대응 중 사용자 화면/관리자 화면에 오류를 보여줄 때

---

## 12. 실제 사용 시나리오

### 12.1 애플리케이션 부팅 시 서비스 준비

```python
from os import environ
from docmesh_py_core import ServiceFactoryRegistry, load_settings

settings = load_settings(environ)
registry = ServiceFactoryRegistry(settings)

postgres = registry.create_client("postgres")
minio = registry.create_client("minio")
keycloak = registry.create_client("keycloak")

postgres.check()
minio.check()
keycloak.check()
```

### 12.2 API 서버 readiness endpoint

```python
from os import environ
from docmesh_py_core import HealthCheckError, ServiceFactoryRegistry, check_all_services, load_settings

settings = load_settings(environ)
registry = ServiceFactoryRegistry(settings)

postgres = registry.create_client("postgres")
minio = registry.create_client("minio")
ollama = registry.create_client("ollama")


def readiness() -> dict:
    try:
        result = check_all_services(
            {
                "postgres": postgres.check,
                "minio": minio.check,
                "ollama": ollama.check,
            },
            required_services={"postgres", "minio"},
        )
    except HealthCheckError as exc:
        return {
            "ok": False,
            "failed_service": exc.service,
            "error": exc.error,
        }

    return {
        "ok": result.ok,
        "services": [
            {
                "service": s.service,
                "ok": s.ok,
                "latency_ms": s.latency_ms,
                "error": s.error,
            }
            for s in result.services
        ],
    }
```

### 12.3 Keycloak bearer token 검증

```python
from os import environ
from docmesh_py_core import KeycloakAuthService, TokenValidationError, load_settings

settings = load_settings(environ)
auth = KeycloakAuthService(settings, allowed_algorithms=["RS256"])


def authenticate(bearer_token: str) -> dict:
    try:
        user = auth.extract_user_info(bearer_token)
    except TokenValidationError as exc:
        raise PermissionError(str(exc)) from exc

    return {
        "sub": user.sub,
        "username": user.preferred_username,
        "realm_roles": user.realm_roles,
        "client_roles": user.client_roles,
    }
```

### 12.4 Langfuse optional 처리

```python
langfuse = registry.create_client("langfuse")

if langfuse is not None:
    langfuse.check()
    # 원본 SDK 메서드 호출 가능
    langfuse.auth_check()
```

---

## 13. 자주 하는 실수

### 13.1 `Settings()`를 바로 생성해도 되나요?

가능은 하지만 권장하지 않는다.

이유:

- `load_settings()`가 서비스별 검증을 한 번에 수행한다.
- 검증 실패 메시지를 더 읽기 쉽게 정리해준다.
- `LANGFUSE_ENVIRONMENT` 기본값 주입 같은 후처리가 포함된다.

### 13.2 `registry.create_client("nats")` 결과를 바로 publish에 써도 되나요?

아니다.

반환값은 연결된 client가 아니라 `NatsConnectionBuilder`다.

올바른 예시:

```python
builder = registry.create_client("nats")
client = await builder.connect()
await client.publish("events.demo", b"payload")
```

### 13.3 `check()` 반환값이 서비스마다 다른가요?

그렇다.

`ServiceClientWrapper.check()`는 내부 health call의 반환값을 그대로 돌려준다.
따라서 공통 구조를 기대하지 말고, "예외 없이 호출이 성공했는가" 중심으로 사용하는 것이 좋다.

### 13.4 Langfuse를 안 쓰면 어떻게 되나요?

`LANGFUSE_ENABLED=false`면 registry에서 `create_client("langfuse")` 결과가 `None`일 수 있다.

### 13.5 운영 환경에서 SSL 검증을 꺼도 되나요?

안 된다.

`DOCMESH_ENV=production|prod`에서 아래 값이 비보안으로 설정되면 `ConfigError`가 발생한다.

- `KEYCLOAK_VERIFY_SSL=false`
- `MINIO_SECURE=false`
- `MILVUS_SECURE=false`

---

## 14. 권장 사용 규칙

- 설정 생성은 `load_settings()`를 단일 진입점으로 사용한다.
- 서비스 생성은 `ServiceFactoryRegistry`를 통해 통일한다.
- 서비스 생존 여부 확인은 서비스별 SDK 메서드 대신 먼저 `check()`를 사용한다.
- 오류 로그나 운영 화면 출력에는 `mask_sensitive_value()` 또는 이미 마스킹된 예외 메시지를 사용한다.
- Keycloak JWT 검증은 직접 구현하지 말고 `KeycloakAuthService.extract_user_info()`를 사용한다.
- 선택 서비스(Langfuse)와 비동기 서비스(NATS)는 일반 동기 서비스와 다르게 취급한다.

---

## 15. 빠른 참조

### 설정

```python
settings = load_settings(env)
```

### 서비스 클라이언트 생성

```python
registry = ServiceFactoryRegistry(settings)
postgres = registry.create_client("postgres")
```

### 공통 health check

```python
postgres.check()
```

### 여러 서비스 health 집계

```python
result = check_all_services({"postgres": postgres.check})
```

### Keycloak access token 요청

```python
token = KeycloakAuthService(settings).fetch_access_token()
```

### Keycloak JWT 검증

```python
user = KeycloakAuthService(settings, allowed_algorithms=["RS256"]).extract_user_info(jwt)
```

### 민감정보 마스킹

```python
safe = mask_sensitive_value(raw_message)
```

---

## 16. 관련 문서

- [설정 가이드](./config.md)
- [테스트 가이드](./test.md)
